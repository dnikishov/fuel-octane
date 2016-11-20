# == Class: octane_tasks::dbsync
#
# This class is for applying latest database migrations
#
class octane_tasks::volume_update_host (
) inherits octane_tasks::params {
  if $octane_tasks::params::orig_version == '7.0' {
    Exec {
      provider => shell,
    }

    exec { 'volume-update-host':
      command => 'source /tmp/cinder_current_host; source /tmp/cinder_new_host; cinder-manage volume update_host --currenthost ${CURRENT_HOST} --newhost ${NEW_HOST}',
    }
  }
}
