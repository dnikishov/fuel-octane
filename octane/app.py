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

import os
import sys

from cliff import app
from cliff import commandmanager as cm

import octane
from octane import log


class OctaneApp(app.App):
    def __init__(self, **kwargs):
        super(OctaneApp, self).__init__(
            description='Octane - upgrade your Fuel',
            version=octane.__version__,
            command_manager=cm.CommandManager('octane'),
            **kwargs
        )

    def build_option_parser(self, description, version, argparse_kwargs=None):
        parser = super(OctaneApp, self).build_option_parser(
            description, version, argparse_kwargs)
        if os.environ.get('OCTANE_DEBUG'):
            parser.set_defaults(debug=True, verbose_level=2)
        if os.getuid() == 0:  # Fuel master anarchy
            log_file = '/var/log/octane.log'
        else:  # Probably local dev's env
            log_file = 'octane.log'
        parser.set_defaults(log_file=log_file)
        return parser

    def configure_logging(self):
        super(OctaneApp, self).configure_logging()
        log.set_console_formatter()
        log.silence_iso8601()
        log.lower_urllib_level()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    return OctaneApp().run(argv)
