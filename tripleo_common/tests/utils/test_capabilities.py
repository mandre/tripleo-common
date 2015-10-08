# Copyright 2015 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from tripleo_common.tests import base
from tripleo_common.utils.capabilities import \
    get_deployment_plan_environments
from tripleo_common.utils.capabilities import \
    update_deployment_plan_environments


class CapabilitiesTest(base.TestCase):
    PLAN_FILES = {
        'capabilities_map.yaml': {
            'contents':
                """topics:
                    - title: Basic Configuration
                      description:
                      environment_groups:
                        - title:
                          description: Enable basic...
                          environments:
                            - file: oc-env.yaml
                              title: Config...
                              description:
                              default: true""",
            'meta': {
                'file-type': 'capabilities-map'
            }
        },
        'oc-env.yaml': {
            'contents': '',
            'meta': {
                'file-type': 'environment',
                'enabled': 'True',
                'order': -1
            }
        }
    }

    def test_get_deployment_plan_environments(self):

        resources = get_deployment_plan_environments(self.PLAN_FILES)
        self.assertEqual(
            {'topics': [{'description': None,
             'environment_groups': [{'description': 'Enable basic...',
                                     'environments': [{'default': True,
                                                       'description': None,
                                                       'enabled': True,
                                                       'file': 'oc-env.yaml',
                                                       'title': 'Config...'}],
                                     'title': None}],
                        'title': 'Basic Configuration'}]},
            resources,
        )

    def test_update_deployment_plan_environments(self):
        selected_resources = {
            'oc-env.yaml': 'False'
        }
        updated_plan_files = update_deployment_plan_environments(
            self.PLAN_FILES, selected_resources)
        self.assertEqual(
            'False',
            updated_plan_files['oc-env.yaml']['meta']['enabled']
        )
