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

from octane.handlers.backup_restore import base
from octane.util import archivate
from octane.util import puppet


class AdminNetworks(base.PathFilterArchivator):
    backup_directory = "/etc/hiera/"
    allowed_files = ["networks.yaml"]
    backup_name = "networks"

    def restore(self):
        networks_member = next(archivate.filter_members(
            self.archive, self.backup_name), None)
        if networks_member is not None:
            super(AdminNetworks, self).restore()
            puppet.apply_task("dhcp-ranges")
