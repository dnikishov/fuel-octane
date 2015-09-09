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


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.install_node.install_node')
    octane_app.run(["install-node", "--isolated", "1", "2", "3", "4",
                    "--network", "public", "management"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2, [3, 4], isolated=True,
                              networks=["public", "management"])


def test_parser_fail_networks(mocker, octane_app):
    m = mocker.patch('octane.util.env.get_env_networks')
    m.return_value = [{'name': 'public'}]
    with pytest.raises(Exception):
        octane_app.run(["install-node", "--isolated", "1", "2", "3", "4",
                        "--network", "public", "management"])
