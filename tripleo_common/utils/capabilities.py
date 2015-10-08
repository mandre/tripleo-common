# Copyright 2015 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import yaml


def get_deployment_plan_environments(plan_files):
    """Get capabilities map with enabled flags for its environment files

    :param plan_files: Template files with its content and meta
    :type plan_files: dict

    :return A mapping file with enabled flags for environments
    """
    mapping = {}

    for template_path, val in plan_files.items():
        file_type = val.get('meta', {}).get('file-type')
        if file_type == 'capabilities-map':
            mapping = yaml.load(plan_files[template_path]['contents'])
            for topic in mapping['topics']:
                for environment_group in topic['environment_groups']:
                    for environment in environment_group['environments']:
                        if plan_files[environment['file']].get('meta', {}).\
                                get('enabled') == 'True':
                            environment['enabled'] = True

    return mapping


def update_deployment_plan_environments(plan_files, environments_flags):
    """Update plan's environment files with enabled flags

    :param plan_files: Plan files
    :type plan_files: dict

    :param environments_flags: Environment paths with enabled flags
    :type environments_flags: dict

    :return updated plan_files
    """

    for environment_path in environments_flags.keys():
        if environment_path in plan_files.keys():
            file_type = plan_files[environment_path].\
                get('meta', {}).get('file-type')
            if file_type == 'environment' or file_type == 'root-environment':
                plan_files[environment_path]['meta']['enabled'] = \
                    environments_flags[environment_path]

    return plan_files
