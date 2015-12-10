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

import json

import mock

from tripleo_common.core import exception
from tripleo_common.core import models
from tripleo_common.tests.api import base

# raw plan data
PLAN_NAME = 'overcloud'
ENVIRONMENT_FILES = {
    '/path/to/environment.yaml': {
        'contents': "parameters:\n"
                    "  one: uno\n"
                    "  obj:\n"
                    "    two: due\n"
                    "    three: tre\n",
        'meta': {'file-type': 'root-environment'},
    },
    '/path/to/network-isolation.json': {
        'contents': '{"parameters": {"one": "one"}}',
        'meta': {'file-type': 'environment', 'order': 1},
    },
    '/path/to/ceph-storage-env.yaml': {
        'contents': "parameters:\n"
                    "  obj:\n"
                    "    two: dos,\n"
                    "    three: three",
        'meta': {'file-type': 'environment', 'order': 2},
    },
    '/path/to/poc-custom-env.yaml': {
        'contents': "parameters:\n"
                    "  obj:\n"
                    "    two: two\n"
                    "  some::resource: /path/to/somefile.yaml",
        'meta': {'file-type': 'environment', 'order': 0}
    },
}
OTHER_FILES = {
    '/path/to/overcloud.yaml': {
        'contents': (
            "heat_template_version: 2015-04-30\n\n"
            "resources:\n"
            "\n"
            "  HorizonSecret:\n"
            "    type: OS::Heat::RandomString\n"
            "    properties:\n"
            "      length: 10\n"
            "\n"
            "  Controller:\n"
            "    type: OS::Heat::ResourceGroup\n"
            "    depends_on: Networks\n"
            "    properties:\n"
            "      count: {get_param: ControllerCount}\n"),
        'meta': {'file-type': 'root-template'},
    },
    'capabilities_map.yaml': {
        'contents': (
            "topics:\n"
            "    - title: Basic Configuration\n"
            "      description:\n"
            "      environment_groups:\n"
            "        - title:\n"
            "          description: Enable basic functionality\n"
            "          environments:\n"
            "            - file: /path/to/environment.yaml\n"
            "              title: Root Environment\n"
            "              description: Root environment\n"
            "              default: true\n"
            "            - file: /path/to/network-isolation.json\n"
            "              title: Network Isolation\n"
            "              description: Network isolation\n"
            "              default: false\n"
            "            - file: /path/to/ceph-storage-env.yaml\n"
            "              title: Ceph\n"
            "              description: ceph\n"
            "              default: false\n"
            "            - file: /path/to/poc-custom-env.yaml\n"
            "              title: Custom\n"
            "              description: custom\n"
            "              default: false\n"),
        'meta': {
            'file-type': 'capabilities-map'
        }
    },
    '/path/to/somefile.yaml': {'contents': "description: lorem ipsum"}
}
PLAN_FILES = ENVIRONMENT_FILES.copy()
PLAN_FILES.update(OTHER_FILES)
PLAN_DATA = {
    'name': PLAN_NAME,
    'files': PLAN_FILES,
    'metadata': {}
}

# expected plan output data
PLAN_LINKS = [{'href': '/v1/plans/' + PLAN_NAME, 'rel': 'self'}]
PLAN_OUTPUT_DATA = PLAN_DATA.copy()
PLAN_OUTPUT_DATA['links'] = PLAN_LINKS
ENV_OUTPUT_DATA = {
    'topics': [
        {'description': None,
         'environment_groups': [
             {'description': 'Enable basic functionality',
              'environments': [
                  {'default': True,
                   'description': 'Root environment',
                   'file': '/path/to/environment.yaml',
                   'title': 'Root Environment'},
                  {'default': False,
                   'description': 'Network isolation',
                   'file': '/path/to/network-isolation.json',
                   'title': 'Network Isolation'},
                  {'default': False,
                   'description': 'ceph',
                   'file': '/path/to/ceph-storage-env.yaml',
                   'title': 'Ceph'},
                  {'default': False,
                   'description': 'custom',
                   'file': '/path/to/poc-custom-env.yaml',
                   'title': 'Custom'}
              ],
              'title': None}
         ],
         'title': 'Basic Configuration'}
    ]
}
PARAMETERS_OUTPUT_DATA = {
    'one': {
        'label': 'one',
        'value': 'one'
    },
    'two': {
        'label': 'two',
        'value': 'two'
    }
}

# plan
PLAN = models.Plan(PLAN_NAME)
PLAN.files = PLAN_FILES


class TestApiPlans(base.BaseAPITest):

    @mock.patch('tripleo_common.core.plan.PlanManager.get_plan_list')
    def test_get_all(self, get_plan_list_mock):
        get_plan_list_mock.return_value = [PLAN_NAME]

        res = self.app.get('/v1/plans')
        self.assertEqual(200, res.status_code)
        self.assertJSONEquals(
            {'plans': [{'name': PLAN_NAME, 'links': PLAN_LINKS}]},
            res.data)
        get_plan_list_mock.assert_called_once_with()

    @mock.patch('tripleo_common.core.plan.PlanManager.get_plan')
    def test_get_one(self, get_plan_mock):
        get_plan_mock.return_value = PLAN

        res = self.app.get('/v1/plans/' + PLAN_NAME)
        self.assertEqual(200, res.status_code)
        self.assertJSONEquals({'plan': PLAN_OUTPUT_DATA}, res.data)
        get_plan_mock.assert_called_once_with(PLAN_NAME)

    @mock.patch('tripleo_common.core.plan.PlanManager.get_plan')
    def test_get_one_doesnt_exist(self, get_plan_mock):

        get_plan_mock.side_effect = exception.PlanDoesNotExistError(
            name=PLAN_NAME)

        res = self.app.get('/v1/plans/' + PLAN_NAME)
        self.assertEqual(404, res.status_code)
        get_plan_mock.assert_called_once_with(PLAN_NAME)
        self.assertJSONEquals({'error': {
            'message': 'A plan with the name overcloud does not exist.'
        }}, res.data)

    @mock.patch('tripleo_common.core.plan.PlanManager.create_plan')
    def test_create(self, create_plan_mock):
        create_plan_mock.return_value = PLAN

        res = self.app.post('/v1/plans', data=json.dumps(PLAN_DATA))
        self.assertEqual(200, res.status_code)
        create_plan_mock.assert_called_once_with(PLAN_NAME, PLAN_FILES)
        self.assertJSONEquals({'plan': PLAN_OUTPUT_DATA}, res.data)

    @mock.patch('tripleo_common.core.plan.PlanManager.create_plan')
    def test_create_already_exists(self, create_plan_mock):

        create_plan_mock.side_effect = exception.PlanAlreadyExistsError(
            name=PLAN_NAME)

        res = self.app.post('/v1/plans', data=json.dumps(PLAN_DATA))
        self.assertEqual(409, res.status_code)
        create_plan_mock.assert_called_once_with(PLAN_NAME, PLAN_FILES)
        self.assertJSONEquals({'error': {
            'message': 'A plan with the name overcloud already exists.'
        }}, res.data)

    @mock.patch('tripleo_common.core.plan.PlanManager.update_plan')
    def test_update(self, update_plan_mock):
        update_plan_mock.return_value = PLAN

        res = self.app.patch('/v1/plans/' + PLAN_NAME,
                             data=json.dumps(PLAN_DATA))
        self.assertEqual(200, res.status_code)
        update_plan_mock.assert_called_once_with(PLAN_NAME, PLAN_FILES)
        self.assertJSONEquals({'plan': PLAN_OUTPUT_DATA}, res.data)

    @mock.patch('tripleo_common.core.plan.PlanManager.update_plan')
    def test_update_doesnt_exist(self, update_plan_mock):
        update_plan_mock.side_effect = exception.PlanDoesNotExistError(
            name=PLAN_NAME)

        res = self.app.patch('/v1/plans/' + PLAN_NAME,
                             data=json.dumps(PLAN_DATA))
        self.assertEqual(404, res.status_code)
        update_plan_mock.assert_called_once_with(PLAN_NAME, PLAN_FILES)
        self.assertJSONEquals({'error': {
            'message': 'A plan with the name overcloud does not exist.'
        }}, res.data)

    @mock.patch('tripleo_common.core.plan.PlanManager.delete_plan')
    def test_delete(self, delete_plan_mock):
        res = self.app.delete('/v1/plans/' + PLAN_NAME)
        self.assertEqual(204, res.status_code)
        delete_plan_mock.assert_called_once_with(PLAN_NAME)

    @mock.patch('tripleo_common.core.plan.PlanManager.delete_plan')
    def test_delete_doesnt_exist(self, delete_plan_mock):
        delete_plan_mock.side_effect = exception.PlanDoesNotExistError(
            name=PLAN_NAME)
        res = self.app.delete('/v1/plans/' + PLAN_NAME)
        self.assertEqual(404, res.status_code)
        delete_plan_mock.assert_called_once_with(PLAN_NAME)
        self.assertJSONEquals({'error': {
            'message': 'A plan with the name overcloud does not exist.'
        }}, res.data)

    @mock.patch('tripleo_common.core.plan.PlanManager.'
                'get_deployment_plan_environments')
    def test_get_environments(self, get_deployment_plan_environments_mock):
        get_deployment_plan_environments_mock.return_value = ENV_OUTPUT_DATA
        res = self.app.get('/v1/plans/' + PLAN_NAME + '/environments')
        self.assertEqual(200, res.status_code)
        self.assertJSONEquals({'environments': ENV_OUTPUT_DATA}, res.data)
        get_deployment_plan_environments_mock.assert_called_once_with(
            PLAN_NAME)

    @mock.patch('tripleo_common.core.plan.PlanManager.'
                'get_deployment_plan_environments')
    @mock.patch('tripleo_common.core.plan.PlanManager.'
                'update_deployment_plan_environments')
    def test_update_environments(self,
                                 update_deployment_plan_environments_mock,
                                 get_deployment_plan_environments_mock):
        get_deployment_plan_environments_mock.return_value = ENV_OUTPUT_DATA
        update_deployment_plan_environments_mock.return_value = PLAN

        res = self.app.patch('/v1/plans/' + PLAN_NAME + '/environments',
                             data=json.dumps(ENV_OUTPUT_DATA))
        self.assertEqual(200, res.status_code)
        self.assertJSONEquals({'environments': ENV_OUTPUT_DATA}, res.data)
        update_deployment_plan_environments_mock.assert_called_once_with(
            PLAN_NAME, ENV_OUTPUT_DATA)
        get_deployment_plan_environments_mock.assert_called_once_with(
            PLAN_NAME)

    @mock.patch(
        'tripleo_common.core.plan.PlanManager.get_deployment_parameters')
    def test_get_parameters(self, get_parameters_mock):
        get_parameters_mock.return_value = PARAMETERS_OUTPUT_DATA

        res = self.app.get('/v1/plans/' + PLAN_NAME + '/parameters')
        self.assertEqual(200, res.status_code)
        self.assertJSONEquals({'parameters': PARAMETERS_OUTPUT_DATA}, res.data)
        get_parameters_mock.assert_called_once_with(PLAN_NAME)

    @mock.patch(
        'tripleo_common.core.plan.PlanManager.get_deployment_parameters')
    @mock.patch(
        'tripleo_common.core.plan.PlanManager.update_deployment_parameters')
    def test_update_parameters(self, update_parameters_mock,
                               get_parameters_mock):
        get_parameters_mock.return_value = PARAMETERS_OUTPUT_DATA
        update_parameters_mock.return_value = PLAN

        res = self.app.patch('/v1/plans/' + PLAN_NAME + '/parameters',
                             data=json.dumps(PARAMETERS_OUTPUT_DATA))
        self.assertEqual(200, res.status_code)
        self.assertJSONEquals({'parameters': PARAMETERS_OUTPUT_DATA}, res.data)
        update_parameters_mock.assert_called_once_with(
            PLAN_NAME,
            PARAMETERS_OUTPUT_DATA)
        get_parameters_mock.assert_called_once_with(PLAN_NAME)
