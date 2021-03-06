# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import pytest
import subprocess

import mock
from octane.tests import util as test_util
from octane.util import network


def test_create_overlay_network(mocker):
    node1 = mocker.MagicMock()
    node1.id = 2
    node1.data = {
        'id': node1.id,
        'cluster': 101,
        'roles': ['controller'],
        'ip': '10.10.10.1',
    }
    node2 = mocker.MagicMock()
    node2.id = 3
    node2.data = {
        'id': node2.id,
        'cluster': 101,
        'roles': [],
        'pending_roles': ['controller'],
        'ip': '10.10.10.2',
    }
    env = mocker.MagicMock()
    env.data = {
        'id': 101,
    }
    deployment_info = [{
        'network_scheme': {
            'transformations': [{
                'action': 'add-br',
                'name': 'br-ex',
                'provider': 'ovs',
            }, {
                'action': 'add-br',
                'name': 'br-mgmt',
            }]
        }
    }]

    mock_ssh = mocker.patch('octane.util.ssh.call')
    mock_ssh.side_effect = [subprocess.CalledProcessError('', ''), None,
                            subprocess.CalledProcessError('', ''), None,
                            None, None, None, None]

    expected_args = [
        mock.call(
            ['sh', '-c',
             'ovs-vsctl list-ports br-ex | grep -q br-ex--gre-10.10.10.2'],
            node=node1),
        mock.call(['ovs-vsctl', 'add-port', 'br-ex', 'br-ex--gre-10.10.10.2',
                   '--', 'set', 'Interface', 'br-ex--gre-10.10.10.2',
                   'type=gre',
                   'options:remote_ip=10.10.10.2',
                   'options:key=2'],
                  node=node1),
        mock.call(['sh', '-c',
                   'ip link show dev gre3-3'],
                  node=node1),
        mock.call(['ip', 'link', 'add', 'gre3-3',
                   'type', 'gretap',
                   'remote', '10.10.10.2',
                   'local', '10.10.10.1',
                   'key', '3'],
                  node=node1),
        mock.call(['ip', 'link', 'set', 'up', 'dev', 'gre3-3'],
                  node=node1),
        mock.call(['ip', 'link', 'set', 'mtu', '1450', 'dev', 'gre3-3', ],
                  node=node1),
        mock.call(['ip', 'link', 'set', 'up', 'dev', 'br-mgmt'], node=node1),
        mock.call(['brctl', 'addif', 'br-mgmt', 'gre3-3'],
                  node=node1),
    ]

    network.create_overlay_networks(node1, node2, env, deployment_info,
                                    node1.id)

    assert mock_ssh.call_args_list == expected_args


def test_delete_overlay_network(mocker):
    node = mock.Mock()
    deployment_info = {
        'network_scheme': {
            'transformations': [{
                'action': 'add-br',
                'name': 'br-ex',
                'provider': 'ovs',
            }, {
                'action': 'add-br',
                'name': 'br-mgmt',
            }]
        }
    }

    mock_ssh = mocker.patch('octane.util.ssh.call')

    mock_ovs_tuns = mocker.patch('octane.util.network.list_tunnels_ovs')
    mock_ovs_tuns.return_value = ['br-ex--gre-10.10.10.2']

    mock_lnx_tun = mocker.patch('octane.util.network.list_tunnels_lnx')
    mock_lnx_tun.return_value = ['gre3-3']

    expected_args = [
        mock.call(['ovs-vsctl', 'del-port', 'br-ex', 'br-ex--gre-10.10.10.2'],
                  node=node),
        mock.call(['brctl', 'delif', 'br-mgmt', 'gre3-3'], node=node),
        mock.call(['ip', 'link', 'delete', 'gre3-3'], node=node),
    ]

    network.delete_overlay_networks(node, deployment_info)

    assert mock_ssh.call_args_list == expected_args


def test_delete_patch_ports(mocker):
    node = mock.Mock()

    mock_ssh = mocker.patch('octane.util.ssh.call')

    expected_args = [
        mock.call(
            ['ovs-vsctl', 'del-port', 'br-ovs-bond1', 'br-ovs-bond1--br-ex'],
            node=node),
        mock.call(['ovs-vsctl', 'del-port', 'br-ex', 'br-ex--br-ovs-bond1'],
                  node=node),
        mock.call(['ovs-vsctl', 'del-port', 'br-ovs-bond2',
                   'br-ovs-bond2--br-mgmt'],
                  node=node),
        mock.call(
            ['ovs-vsctl', 'del-port', 'br-mgmt', 'br-mgmt--br-ovs-bond2'],
            node=node),
    ]

    network.delete_patch_ports(node, DEPLOYMENT_INFO_5_1)

    assert mock_ssh.call_args_list == expected_args


def test_delete_lnx_ports(mocker):
    node = mock.Mock()

    mock_ssh = mocker.patch('octane.util.ssh.call')

    expected_args = [
        mock.call(['brctl', 'delif', 'br-ex', 'eth0.130'],
                  node=node),
        mock.call(['brctl', 'delif', 'br-mgmt', 'eth1.220'],
                  node=node),
    ]

    network.delete_patch_ports(node, DEPLOYMENT_INFO_7_0)

    assert mock_ssh.call_args_list == expected_args


def test_create_patch_ports_5_1(mocker):
    node = mock.Mock()

    mock_ssh = mocker.patch('octane.util.ssh.call')

    expected_args = [
        mock.call(
            ['ovs-vsctl', 'add-port', 'br-ex', 'br-ex--br-ovs-bond1',
             'trunks=[0]', '--', 'set', 'interface', 'br-ex--br-ovs-bond1',
             'type=patch', 'options:peer=br-ovs-bond1--br-ex'],
            node=node),
        mock.call(
            ['ovs-vsctl', 'add-port', 'br-ovs-bond1', 'br-ovs-bond1--br-ex',
             'trunks=[0]', '--', 'set', 'interface', 'br-ovs-bond1--br-ex',
             'type=patch', 'options:peer=br-ex--br-ovs-bond1'],
            node=node),
        mock.call(
            ['ovs-vsctl', 'add-port', 'br-mgmt', 'br-mgmt--br-ovs-bond2',
             '--', 'set', 'interface', 'br-mgmt--br-ovs-bond2', 'type=patch',
             'options:peer=br-ovs-bond2--br-mgmt'],
            node=node),
        mock.call(
            ['ovs-vsctl', 'add-port', 'br-ovs-bond2', 'br-ovs-bond2--br-mgmt',
             'tag=102', '--', 'set', 'interface', 'br-ovs-bond2--br-mgmt',
             'type=patch', 'options:peer=br-mgmt--br-ovs-bond2'],
            node=node)
    ]

    network.create_patch_ports(node, DEPLOYMENT_INFO_5_1)

    assert mock_ssh.call_args_list == expected_args


def test_create_patch_ports_7_0(mocker):
    node = mock.Mock()

    mock_ssh = mocker.patch('octane.util.ssh.call')

    expected_args = [
        mock.call(
            ['ovs-vsctl', 'add-port', 'br-ex', 'br-ex--br-ovs-bond1', '--',
             'set', 'interface', 'br-ex--br-ovs-bond1', 'type=patch',
             'options:peer=br-ovs-bond1--br-ex'],
            node=node),
        mock.call(
            ['ovs-vsctl', 'add-port', 'br-ovs-bond1', 'br-ovs-bond1--br-ex',
             '--', 'set', 'interface', 'br-ovs-bond1--br-ex', 'type=patch',
             'options:peer=br-ex--br-ovs-bond1'],
            node=node),
        mock.call(
            ['ovs-vsctl', 'add-port', 'br-mgmt', 'br-mgmt--br-ovs-bond2',
             '--', 'set', 'interface', 'br-mgmt--br-ovs-bond2', 'type=patch',
             'options:peer=br-ovs-bond2--br-mgmt'],
            node=node),
        mock.call(
            ['ovs-vsctl', 'add-port', 'br-ovs-bond2', 'br-ovs-bond2--br-mgmt',
             'tag=102', '--', 'set', 'interface', 'br-ovs-bond2--br-mgmt',
             'type=patch', 'options:peer=br-mgmt--br-ovs-bond2'],
            node=node)
    ]

    network.create_patch_ports(node, DEPLOYMENT_INFO_OVS_7_0)

    assert mock_ssh.call_args_list == expected_args


DEPLOYMENT_INFO_5_1 = {
    'openstack_version': '2014.1.3-5.1.1',
    'network_scheme': {
        'transformations': [{
            'action': 'add-br',
            'name': 'br-ex',
        }, {
            'action': 'add-patch',
            'bridges': [
                'br-ovs-bond1',
                'br-ex'
            ],
            'trunks': [
                0
            ]
        }, {
            'action': 'add-patch',
            'bridges': [
                'br-ovs-bond2',
                'br-mgmt'
            ],
            'tags': [
                102,
                0
            ]
        }, {
            'action': 'add-br',
            'name': 'br-mgmt',
        }]
    }
}


DEPLOYMENT_INFO_OVS_7_0 = {
    'openstack_version': '2015.1.0-7.0',
    'network_scheme': {
        'transformations': [{
            'action': 'add-br',
            'name': 'br-ex',
            'provider': 'ovs',
        }, {
            'action': 'add-patch',
            'bridges': [
                'br-ovs-bond1',
                'br-ex'
            ],
            'vlan_ids': [
                0,
                0
            ]
        }, {
            'action': 'add-patch',
            'bridges': [
                'br-ovs-bond2',
                'br-mgmt'
            ],
            'vlan_ids': [
                102,
                0
            ]
        }, {
            'action': 'add-br',
            'name': 'br-mgmt',
            'provider': 'ovs'
        }]
    }
}

DEPLOYMENT_INFO_7_0 = {
    'openstack_version': '2015.1.0-7.0',
    'network_scheme': {
        'transformations': [{
            'action': 'add-br',
            'name': 'br-ex',
        }, {
            'action': 'add-port',
            'name': 'eth0.130',
            'bridge': 'br-ex'
        }, {
            'action': 'add-br',
            'name': 'br-mgmt',
        }, {
            'action': 'add-port',
            'name': 'eth1.220',
            'bridge': 'br-mgmt'
        }]
    }
}


IFACE_BASE = b"auto br-ex\niface br-ex inet static\n"
IFACE_ADDR = b"address 10.109.1.4/24\ngateway 10.109.1.1\n"
IFACE_SINGLEPORT = IFACE_BASE + b"bridge_ports eth0\n"
IFACE_DEFAULT = IFACE_SINGLEPORT + IFACE_ADDR
IFACE_TESTPORT = b"bridge_ports test-iface\n"
IFACE_MULTIPORT = IFACE_BASE + IFACE_TESTPORT
IFACE_MULTIPORT_EXPECTED = IFACE_BASE + b"bridge_ports eth0 test-iface\n"


@pytest.mark.parametrize("content,expected_content", [
    (IFACE_BASE, IFACE_SINGLEPORT),
    (IFACE_DEFAULT, IFACE_DEFAULT),
    (IFACE_MULTIPORT, IFACE_MULTIPORT_EXPECTED),
])
@pytest.mark.parametrize("bridge,port", [
    ('br-ex', {'name': 'eth0'}),
])
def test_save_port_lnx(mocker, node, content, expected_content, bridge, port):
    filename = '/etc/network/interfaces.d/ifcfg-{0}'.format(bridge)
    with test_util.mock_update_file(mocker, node, content, expected_content,
                                    filename):
        network.save_port_lnx(node, bridge, port)
