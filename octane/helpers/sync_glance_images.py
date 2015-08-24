import logging
import yaml
from octane.commands.upgrade_db import get_controllers
from fuelclient.objects import environment as environment_obj
from octane.util import ssh
from octane.util import subprocess

LOG = logging.getLogger(__name__)


def get_astute_yaml(node):
    data = None
    with ssh.sftp(node).open('/etc/astute.yaml') as f:
        data = f.read()
    return yaml.load(data)


def get_endpoint_ip(ep_name, yaml_data):
    if ep_name not in yaml_data['network_scheme']['endpoints']:
        return None
    net_data = yaml_data['network_scheme']['endpoints'][ep_name]["IP"][0]
    if net_data:
        return net_data.split('/')[0]


def get_glance_password(yaml_data):
    return yaml_data['glance']['user_password']


def parse_keystone_get(output, field):
    for line in output.splitlines()[3:-1]:
        parts = line.split()
        if parts[1] == field:
            return parts[3]
    raise Exception(
        "Field {0} not found in output:\n{1}".format(field, output))


def get_tenant_id(node, tenant):
    cmd = ". /root/openrc; keystone tenant-get {0}".format(tenant)
    tenant_info, _ = ssh.call(["sh", "-c", cmd],
                              stdout=ssh.PIPE,
                              node=node)
    return parse_keystone_get(tenant_info, 'id')


def get_swift_objects(node, tenant, user, password, token, container):
    cmd = ". /root/openrc; swift --os-project-name {0} --os-username {1}"\
        " --os-password {2} --os-auth-token {3} list {4}".format(tenant,
                                                                 user,
                                                                 password,
                                                                 token,
                                                                 container)
    objects_list, _ = ssh.call(["sh", "-c", cmd],
                               stdout=ssh.PIPE,
                               node=node)
    return objects_list.split('\n')[:-1]


def get_auth_token(node, tenant, user, password):
    cmd = ". /root/openrc; keystone --os-tenant-name {0}"\
        " --os-username {1} --os-password {2} token-get".format(tenant,
                                                                user,
                                                                password)
    token_info, _ = ssh.call(["sh", "-c", cmd],
                             stdout=ssh.PIPE,
                             node=node)
    return parse_keystone_get(token_info, 'id')


def download_image(node, tenant, user, password, token, container, object_id):
    cmd = ". /root/openrc; swift --os-project-name {0} --os-username {1}"\
        " --os-password {2} --os-auth-token {3} download {4} {5}"\
        .format(tenant,
                user,
                password,
                token,
                container,
                object_id)
    ssh.call(["sh", "-c", cmd], node=node)
    LOG.info("Swift %s image has been downloaded" % object_id)


def delete_image(node, tenant, user, password, token, container, object_id):
    cmd = ". /root/openrc; swift --os-project-name {0}"\
        " --os-username {1} --os-password {2} --os-auth-token {3}"\
        " delete {4} {5}".format(tenant, user, password, token,
                                 container, object_id)
    ssh.call(["sh", "-c", cmd], node=node)
    LOG.info("Swift %s image has been deleted" % object_id)


def transfer_image(node, tenant, user, password, token, container, object_id,
                   storage_ip, tenant_id):
    storage_url = "http://{0}:8080/v1/AUTH_{1}".format(storage_ip, tenant_id)
    cmd = ['swift', '--os-project-name', tenant, '--os-username', user,
           '--os-password', password, '--os-auth-token', token,
           '--os-storage-url', storage_url, 'upload', container,
           object_id]
    ssh.call(cmd, node=node)
    LOG.info("Swift %s image has been transferred" % object_id)


def sync_glance_images(source_env_id, seed_env_id, source_glance_user,
                       seed_glance_user, seed_swift_ep):
    """Sync glance images from original ENV to seed ENV

    Args:
        source_env_id (int): ID of original ENV.
        seed_env_id (int): ID of seed ENV.
        source_glance_user (str): glance user of original ENV.
        seed_glance_user (str): glance user of seed ENV.
        seed_swift_ep (str): endpoint's name where swift-proxy service is
                             listening on.

    Examples:
        sync_glance_images(2, 3, 'glance', 'glance', 'br-mgmt')
    """
    # set swift container value
    container = "glance"
    # choose tenant
    tenant = "services"
    # get clusters by id
    source_env = environment_obj.Environment(source_env_id)
    seed_env = environment_obj.Environment(seed_env_id)
    # gather cics admin IPs
    source_node = next(get_controllers(source_env))
    seed_node = next(get_controllers(seed_env))
    # get cics yaml files
    source_yaml = get_astute_yaml(source_node)
    seed_yaml = get_astute_yaml(seed_node)
    # get glance passwords
    source_glance_pass = get_glance_password(source_yaml)
    seed_glance_pass = get_glance_password(seed_yaml)
    # get seed node swift ip
    seed_swift_ip = get_endpoint_ip(seed_swift_ep, seed_yaml)
    # get service tenant id & lists of objects for source env
    source_token = get_auth_token(source_node, tenant, source_glance_user,
                                  source_glance_pass)
    source_swift_list = set(get_swift_objects(source_node,
                                              tenant,
                                              source_glance_user,
                                              source_glance_pass,
                                              source_token,
                                              container))
    # get service tenant id & lists of objects for seed env
    seed_token = get_auth_token(seed_node, tenant, seed_glance_user,
                                seed_glance_pass)
    seed_swift_list = set(get_swift_objects(seed_node,
                                            tenant,
                                            seed_glance_user,
                                            seed_glance_pass,
                                            seed_token,
                                            container))
    # get service tenant for seed env
    seed_tenant = get_tenant_id(seed_node, tenant)
    # migrate new images
    for image in source_swift_list - seed_swift_list:
        # download image on source's node local drive
        source_token = get_auth_token(source_node, tenant, source_glance_user,
                                      source_glance_pass)
        download_image(source_node, tenant, source_glance_user,
                       source_glance_pass, source_token, container, image)
        # transfer image
        source_token = get_auth_token(source_node, tenant,
                                      source_glance_user,
                                      source_glance_pass)
        seed_token = get_auth_token(seed_node, tenant, seed_glance_user,
                                    seed_glance_pass)
        transfer_image(source_node, tenant, seed_glance_user, seed_glance_pass,
                       seed_token, container, image, seed_swift_ip,
                       seed_tenant)
        # remove transferred image
        ssh.sftp(source_node).remove(image)
    # delete outdated images
    for image in seed_swift_list - source_swift_list:
        token = get_auth_token(seed_node, tenant, seed_glance_user,
                               seed_glance_pass)
        delete_image(seed_node, tenant, seed_glance_user, seed_glance_pass,
                     token, container, image)
