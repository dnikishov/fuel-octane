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

import re

import yaml

from octane import magic_consts


def merge_dicts(base_dict, update_dict):
    result = base_dict.copy()
    for key, val in update_dict.iteritems():
        if key not in result or not isinstance(result[key], dict):
            result[key] = val
        else:
            result[key] = merge_dicts(result[key], val)
    return result


def get_astute_dict():
    return load_yaml(magic_consts.ASTUTE_YAML)


def load_yaml(filename):
    with open(filename, "r") as f:
        return yaml.load(f)


def iterate_parameters(fp):
    section = None
    for line in fp:
        match = re.match(r'^\s*\[(?P<section>[^\]]+)', line)
        if match:
            section = match.group('section')
            yield line, section, None, None
            continue
        match = re.match(r'^\s*(?P<parameter>[^=\s]+)\s*='
                         '\s*(?P<value>[^\s.+](?:\s*[^\s.+])*)\s*$', line)
        if match:
            parameter, value = match.group("parameter", "value")
            yield line, section, parameter, value
            continue
        yield line, section, None, None


def get_parameters(fp, parameters_to_get):
    parameters_map = {}
    for key, values in parameters_to_get.items():
        for value in values:
            parameters_map[value] = key
    parameters = {}
    for _, section, parameter, value in iterate_parameters(fp):
        parameter_name = parameters_map.get((section, parameter))
        if parameter_name is not None and value is not None:
            parameters[parameter_name] = value
    return parameters


def normalized_cliff_show_json(data):
    if isinstance(data, list):
        return {i['Field']: i['Value'] for i in data}
    return data
