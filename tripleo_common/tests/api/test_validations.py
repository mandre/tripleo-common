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

import datetime
import json
import mock
import time

from swiftclient import exceptions as swiftexceptions

from tripleo_common.tests.api import base

VALID_UUID = 2
INVALID_UUID = 100
REQUIRED_PLAN_UUID = 1
NO_REQUIRED_PLAN_UUID = 2
WITH_METADATA_UUID = 1
NO_METADATA_UUID = 3

MIXED_STAGE = 1
REQUIRED_PLAN_STAGE = 3
NO_REQUIRED_PLAN_STAGE = 2
WITH_METADATA_STAGE = 1
NO_METADATA_STAGE = 3

GET_PLAN_METHOD = \
    'tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get'
VALIDATION_RUN_METHOD = 'tripleo_common.utils.ansible_runner.run'


def passing_validation(*args):
    return {'hostname': {'success': True}}


def failing_validation(*args):
    return {'hostname': {'success': False}}


def running_validation(*args):
    time.sleep(0.1)
    return {}


def wait_for_request_to_be_processed(sleep_time=0.01):
    # Wait for a previous request to be processes
    # This is an ugly hack to deal with concurency issues
    time.sleep(sleep_time)


def options_from_kwargs(kwargs):
    if kwargs:
        return "?" + "&".join(
            ["{}={}".format(k, v) for k, v in kwargs.items()])
    else:
        return ""


class TestApiValidations(base.BaseAPITest):

    def validate_generic_validation(self, validation):
        self.assertIn('uuid', validation)
        self.assertIn('name', validation)
        self.assertIn('description', validation)
        self.assertIn('ref', validation)
        self.assertIn('status', validation)
        self.assertIn('results', validation)
        self.assertIsInstance(validation['results'], list)
        self.assertIn('latest_result', validation)
        self.assertIsInstance(validation['latest_result'], dict)
        self.assertIn('metadata', validation)
        self.assertIsInstance(validation['metadata'], dict)

        if validation['results']:
            result_ref = validation['results'][-1]
            result = self.json_response(self.app.get(result_ref))['result']
            if validation['status'] != 'requires_plan_id':
                self.assertEqual(result, validation['latest_result'])
            self.assertEqual(result['validation'], validation['ref'])

    def validate_new_validation(self, validation):
        self.validate_generic_validation(validation)
        self.assertDictContainsSubset(
            {
                'status': 'new',
                'results': [],
                'latest_result': {},
            }, validation)

    def validate_successful_validation(self, validation):
        self.validate_generic_validation(validation)
        self.assertEqual('success', validation['status'])
        self.validate_successful_result(validation['latest_result'])

    def validate_failing_validation(self, validation):
        self.validate_generic_validation(validation)
        self.assertEqual('failed', validation['status'])
        self.validate_failed_result(validation['latest_result'])

    def validate_running_validation(self, validation):
        self.validate_generic_validation(validation)
        self.assertEqual('running', validation['status'])
        self.validate_running_result(validation['latest_result'])

    def validate_canceled_validation(self, validation):
        self.validate_generic_validation(validation)
        self.assertEqual('canceled', validation['status'])
        self.validate_canceled_result(validation['latest_result'])

    def validate_validation_with_plan_missing_plan_id(self, validation):
        self.validate_generic_validation(validation)
        self.assertDictContainsSubset(
            {
                'status': 'requires_plan_id',
                'latest_result': {},
            }, validation)

    def validate_validation_with_plan(self, validation, plan_id):
        self.validate_generic_validation(validation)
        self.assertNotEqual('requires_plan_id', validation['status'])
        all_results = [self.json_response(self.app.get(result_ref))['result']
                       for result_ref in validation['results']]
        self.assertTrue(all(result['plan_id'] == plan_id
                            for result in all_results))

    def validate_generic_stage(self, stage):
        self.assertIn('uuid', stage)
        self.assertIn('name', stage)
        self.assertIn('description', stage)
        self.assertIn('ref', stage)
        self.assertIn('status', stage)
        self.assertIn('validations', stage)
        self.assertIsInstance(stage['validations'], list)

    def validate_new_stage(self, stage):
        self.validate_generic_stage(stage)
        self.assertEqual('new', stage['status'])
        for validation in stage['validations']:
            self.validate_new_validation(validation)

    def validate_successful_stage(self, stage):
        self.validate_generic_stage(stage)
        self.assertEqual('success', stage['status'])
        for validation in stage['validations']:
            self.validate_successful_validation(validation)

    def validate_failing_stage(self, stage):
        self.validate_generic_stage(stage)
        self.assertEqual('failed', stage['status'])
        all_statuses = [v['status'] for v in stage['validations']]
        self.assertFalse(any(status == 'requires_plan_id'
                             for status in all_statuses))
        self.assertFalse(any(status == 'running' for status in all_statuses))
        self.assertTrue(any(status == 'failed' for status in all_statuses))

    def validate_running_stage(self, stage):
        self.validate_generic_stage(stage)
        self.assertEqual('running', stage['status'])
        all_statuses = [v['status'] for v in stage['validations']]
        self.assertFalse(any(status == 'requires_plan_id'
                             for status in all_statuses))
        self.assertTrue(any(status == 'running' for status in all_statuses))

    def validate_canceled_stage(self, stage):
        self.validate_generic_stage(stage)
        self.assertEqual('canceled', stage['status'])
        all_statuses = [v['status'] for v in stage['validations']]
        self.assertFalse(any(status == 'requires_plan_id'
                             for status in all_statuses))
        self.assertFalse(any(status == 'running' for status in all_statuses))
        self.assertFalse(any(status == 'failed' for status in all_statuses))
        self.assertTrue(any(status == 'canceled' for status in all_statuses))

    def validate_stage_with_plan_missing_plan_id(self, stage):
        self.validate_generic_stage(stage)
        self.assertEqual('requires_plan_id', stage['status'])
        all_statuses = [v['status'] for v in stage['validations']]
        self.assertTrue(any(status == 'requires_plan_id'
                            for status in all_statuses))

    def validate_stage_with_plan(self, stage, plan_id):
        self.validate_generic_stage(stage)
        self.assertNotEqual('requires_plan_id', stage['status'])
        for validation in stage['validations']:
            self.validate_validation_with_plan(validation, plan_id)

    def validate_generic_result(self, result):
        self.assertIn('uuid', result)
        self.assertIn('date', result)
        datetime.datetime.strptime(result['date'], "%Y-%m-%dT%H:%M:%S.%fZ")
        self.assertIn('status', result)
        self.assertIn('detailed_description', result)
        self.assertIn('validation', result)
        self.assertIn('plan_id', result)

    def validate_successful_result(self, result):
        self.validate_generic_result(result)
        self.assertEqual('success', result['status'])
        self.assertEqual(passing_validation(), result['detailed_description'])

    def validate_running_result(self, result):
        self.validate_generic_result(result)
        self.assertEqual('running', result['status'])
        # TODO(mandre) Get partial results in detailed_description
        self.assertEqual({}, result['detailed_description'])

    def validate_failed_result(self, result):
        self.validate_generic_result(result)
        self.assertEqual('failed', result['status'])
        self.assertEqual(failing_validation(), result['detailed_description'])

    def validate_canceled_result(self, result):
        self.validate_generic_result(result)
        self.assertEqual('canceled', result['status'])
        # TODO(mandre) Get partial results in detailed_description
        self.assertEqual({}, result['detailed_description'])

    def json_response(self, response, code=200):
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.status_code, code)
        return json.loads(response.data)

    def run_validation(self, uuid, side_effect, **kwargs):
        with mock.patch(VALIDATION_RUN_METHOD) as validation_run_mock:
            validation_run_mock.side_effect = side_effect
            opts = options_from_kwargs(kwargs)
            self.app.put('/v1/validations/{}/run{}'.format(uuid, opts))
            wait_for_request_to_be_processed()

    def get_validations(self, **kwargs):
        opts = options_from_kwargs(kwargs)
        json = self.json_response(
            self.app.get('/v1/validations/{}'.format(opts)))
        return json['validations']

    def get_validation(self, uuid, **kwargs):
        opts = options_from_kwargs(kwargs)
        json = self.json_response(
            self.app.get('/v1/validations/{}/{}'.format(uuid, opts)))
        return json['validation']

    def run_stage(self, uuid, side_effect, **kwargs):
        with mock.patch(VALIDATION_RUN_METHOD) as validation_run_mock:
            validation_run_mock.side_effect = side_effect
            opts = options_from_kwargs(kwargs)
            self.app.put('/v1/stages/{}/run{}'.format(uuid, opts))
            wait_for_request_to_be_processed()

    def get_stages(self, **kwargs):
        opts = options_from_kwargs(kwargs)
        json = self.json_response(self.app.get('/v1/stages/{}'.format(opts)))
        return json['stages']

    def get_stage(self, uuid, **kwargs):
        opts = options_from_kwargs(kwargs)
        json = self.json_response(
            self.app.get('/v1/stages/{}/{}'.format(uuid, opts)))
        return json['stage']

    def get_results(self, **kwargs):
        opts = options_from_kwargs(kwargs)
        json = self.json_response(
            self.app.get('/v1/validation_results/{}'.format(opts)))
        return json['results']

    def test_list_validations(self):
        rv = self.app.get('/v1/validations/')
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(len(self.json_response(rv)['validations']), 3)

    def test_list_validations_with_unknown_plan(self):
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.get('/v1/validations/?plan_id=invalid')
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    # XXX(mandre) not sure it's wise to sort by ID in case we switch to more
    # complex IDs, like UUIDs
    def test_list_validations_sorted(self):
        validations = self.get_validations()
        self.assertEqual([v['uuid'] for v in validations], ['1', '2', '3'])

    def test_list_validations_metadata(self):
        json = self.get_validations()[WITH_METADATA_UUID - 1]
        self.validate_validation_with_plan_missing_plan_id(json)
        self.assertEqual(json['uuid'], str(WITH_METADATA_UUID))
        self.assertNotEqual(json['name'], 'Unnamed')
        self.assertNotEqual(json['description'], 'No description')
        for (k, v) in json.items():
            self.assertLessEqual(len(bytes(k)), 255)
            self.assertLessEqual(len(bytes(v)), 255)
        # TODO(mandre) check for custom metadata
        # They are in the same metadata section as core metadata
        # Check limit of 255 bytes for key and value

    def test_list_validations_missing_metadata(self):
        json = self.get_validations()[NO_METADATA_UUID - 1]
        self.validate_validation_with_plan_missing_plan_id(json)
        self.assertEqual(json['uuid'], str(NO_METADATA_UUID))
        self.assertEqual(json['name'], 'Unnamed')
        self.assertEqual(json['description'], 'No description')
        self.assertEqual(json['require_plan'], True)
        self.assertEqual(json['metadata'], {})

    def test_list_validations_require_plan(self):
        json = self.get_validations()[REQUIRED_PLAN_UUID - 1]
        self.validate_validation_with_plan_missing_plan_id(json)
        self.assertEqual(json['uuid'], str(REQUIRED_PLAN_UUID))
        self.assertEqual(json['require_plan'], True)

    def test_list_validations_not_require_plan(self):
        json = self.get_validations()[NO_REQUIRED_PLAN_UUID - 1]
        self.validate_new_validation(json)
        self.assertEqual(json['uuid'], str(NO_REQUIRED_PLAN_UUID))
        self.assertEqual(json['require_plan'], False)

    def test_get_validation(self):
        rv = self.app.get('/v1/validations/{}/'.format(VALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.json_response(rv)

    def test_get_unknown_validation(self):
        rv = self.app.get('/v1/validations/{}/'.format(INVALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.json_response(rv, 404)

    def test_get_validation_with_unknown_plan(self):
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.get('/v1/validations/{}/?plan_id=invalid'
                              .format(VALID_UUID))
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    def test_get_new_validation_content(self):
        validation = self.get_validation(VALID_UUID)
        self.validate_new_validation(validation)
        self.assertEqual(str(VALID_UUID), validation['uuid'])

    def test_validation_run(self):
        with mock.patch(VALIDATION_RUN_METHOD) as validation_run_mock:
            validation_run_mock.side_effect = passing_validation
            rv = self.app.put('/v1/validations/{}/run'.format(VALID_UUID))
            self.assertEqual(rv.status_code, 204)
            wait_for_request_to_be_processed()
            self.assertEqual(validation_run_mock.call_count, 1)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_validation_run_with_plan(self, get_plan_mock):
        get_plan_mock.return_value = True
        with mock.patch(VALIDATION_RUN_METHOD) as validation_run_mock:
            validation_run_mock.side_effect = passing_validation
            rv = self.app.put('/v1/validations/{}/run?plan_id=plan1'
                              .format(REQUIRED_PLAN_UUID))
            self.assertEqual(rv.status_code, 204)
            wait_for_request_to_be_processed()
            self.assertEqual(validation_run_mock.call_count, 1)

    def test_run_unknown_validation(self):
        rv = self.app.put('/v1/validations/{}/run'.format(INVALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.json_response(rv, 404)

    def test_run_validation_with_unknown_plan(self):
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.put('/v1/validations/{}/run?plan_id=invalid'
                              .format(VALID_UUID))
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    def test_get_running_validation_content(self):
        self.run_validation(VALID_UUID, running_validation)
        validation = self.get_validation(VALID_UUID)
        self.validate_running_validation(validation)
        self.assertEqual(str(VALID_UUID), validation['uuid'])

    def test_get_successful_validation_content(self):
        self.run_validation(VALID_UUID, passing_validation)
        validation = self.get_validation(VALID_UUID)
        self.validate_successful_validation(validation)
        self.assertEqual(str(VALID_UUID), validation['uuid'])

    def test_get_failed_validation_content(self):
        self.run_validation(VALID_UUID, failing_validation)
        validation = self.get_validation(VALID_UUID)
        self.validate_failing_validation(validation)
        self.assertEqual(str(VALID_UUID), validation['uuid'])

    def test_reject_validation_missing_plan(self):
        with mock.patch(VALIDATION_RUN_METHOD) as validation_run_mock:
            validation_run_mock.side_effect = passing_validation
            rv = self.app.put('/v1/validations/{}/run'
                              .format(REQUIRED_PLAN_UUID))
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    def test_validation_stop_running(self):
        self.run_validation(VALID_UUID, running_validation)

        rv = self.app.put('/v1/validations/{}/stop'.format(VALID_UUID))
        self.assertEqual(rv.status_code, 204)

        validation = self.get_validation(VALID_UUID)
        self.validate_canceled_validation(validation)
        self.assertEqual(str(VALID_UUID), validation['uuid'])

    def test_validation_stop_non_running(self):
        rv = self.app.put('/v1/validations/{}/stop'.format(VALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 400)

    def test_validation_stop_unknown(self):
        rv = self.app.put('/v1/validations/{}/stop'.format(INVALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 404)

    def test_validation_stop_with_unknown_plan(self):
        self.run_validation(NO_REQUIRED_PLAN_UUID, running_validation)
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.put('/v1/validations/{}/stop?plan_id=invalid'
                              .format(NO_REQUIRED_PLAN_UUID))
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_validation_stop_with_plan_id(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_validation(REQUIRED_PLAN_UUID,
                            running_validation, plan_id='plan1')
        rv = self.app.put('/v1/validations/{}/stop?plan_id=plan1'
                          .format(REQUIRED_PLAN_UUID))
        self.assertEqual(rv.status_code, 204)

        validation = self.get_validation(REQUIRED_PLAN_UUID, plan_id='plan1')
        self.validate_canceled_validation(validation)
        self.assertEqual(str(REQUIRED_PLAN_UUID), validation['uuid'])

    def test_validation_stop_missing_plan_id(self):
        self.run_validation(REQUIRED_PLAN_UUID,
                            running_validation, plan_id='plan1')
        rv = self.app.put('/v1/validations/{}/stop'.format(REQUIRED_PLAN_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 404)

    def test_validation_rerun_running(self):
        self.run_validation(VALID_UUID, running_validation)

        rv = self.app.put('/v1/validations/{}/run'.format(VALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 400)

        validation = self.get_validation(VALID_UUID)
        self.validate_running_validation(validation)
        self.assertEqual(str(VALID_UUID), validation['uuid'])

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_validation_rerun_running_with_plan(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_validation(VALID_UUID, running_validation, plan_id='plan1')

        rv = self.app.put('/v1/validations/{}/run?plan_id=plan1'
                          .format(VALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 400)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_validation_without_plan_can_not_run_in_parallel(self,
                                                             get_plan_mock):
        get_plan_mock.return_value = True
        self.run_validation(NO_REQUIRED_PLAN_UUID,
                            running_validation, plan_id='plan1')

        rv = self.app.put('/v1/validations/{}/run?plan_id=plan2'
                          .format(NO_REQUIRED_PLAN_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 400)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_validation_with_plan_can_run_in_parallel(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_validation(REQUIRED_PLAN_UUID,
                            running_validation, plan_id='plan1')

        rv = self.app.put('/v1/validations/{}/run?plan_id=plan2'
                          .format(REQUIRED_PLAN_UUID))
        self.assertEqual(rv.status_code, 204)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_filter_validation_results(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_validation(REQUIRED_PLAN_UUID,
                            passing_validation, plan_id='plan1')
        self.run_validation(REQUIRED_PLAN_UUID,
                            failing_validation, plan_id='plan2')
        validation_plan1 = self.get_validation(REQUIRED_PLAN_UUID,
                                               plan_id='plan1')
        validation_plan2 = self.get_validation(REQUIRED_PLAN_UUID,
                                               plan_id='plan2')

        self.validate_validation_with_plan(validation_plan1, 'plan1')
        self.validate_validation_with_plan(validation_plan2, 'plan2')
        self.validate_successful_validation(validation_plan1)
        self.validate_failing_validation(validation_plan2)

    def test_validation_require_plan_status(self):
        self.run_validation(REQUIRED_PLAN_UUID,
                            passing_validation, plan_id='plan1')
        validation_no_plan = self.get_validation(REQUIRED_PLAN_UUID)
        self.validate_validation_with_plan_missing_plan_id(validation_no_plan)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_filter_validations_results(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_validation(REQUIRED_PLAN_UUID,
                            passing_validation, plan_id='plan1')
        self.run_validation(REQUIRED_PLAN_UUID,
                            failing_validation, plan_id='plan2')

        validation_plan1 = \
            next(v for v in self.get_validations(plan_id='plan1')
                 if v['uuid'] == str(REQUIRED_PLAN_UUID))
        validation_plan2 = \
            next(v for v in self.get_validations(plan_id='plan2')
                 if v['uuid'] == str(REQUIRED_PLAN_UUID))
        validation_no_plan = \
            next(v for v in self.get_validations()
                 if v['uuid'] == str(REQUIRED_PLAN_UUID))

        self.validate_validation_with_plan(validation_plan1, 'plan1')
        self.validate_validation_with_plan(validation_plan2, 'plan2')
        self.validate_successful_validation(validation_plan1)
        self.validate_failing_validation(validation_plan2)
        self.validate_validation_with_plan_missing_plan_id(validation_no_plan)

        self.assertEqual(len(validation_plan1['results']), 1)
        self.assertEqual(len(validation_plan2['results']), 1)
        self.assertEqual(len(validation_no_plan['results']), 2)

    ########
    # STAGES
    ########

    def test_list_stages(self):
        stages = self.get_stages()
        self.assertEqual(len(stages), 3)

    def test_list_stages_with_unknown_plan(self):
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.get('/v1/stages/?plan_id=invalid')
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    # XXX(mandre) not sure it's wise to sort by ID in case we switch to more
    # complex IDs, like UUIDs
    def test_list_stages_sorted(self):
        stages = self.get_stages()
        self.assertEqual([s['uuid'] for s in stages], ['1', '2', '3'])

    def test_list_stages_metadata(self):
        json = self.get_stages()[WITH_METADATA_STAGE - 1]
        self.assertEqual(json['uuid'], str(WITH_METADATA_STAGE))
        self.assertNotEqual(json['name'], 'Unnamed')
        self.assertNotEqual(json['description'], 'No description')
        self.assertNotEqual(json['stage'], 'No stage')

    def test_list_stages_missing_metadata(self):
        json = self.get_stages()[NO_METADATA_STAGE - 1]
        self.assertEqual(json['uuid'], str(NO_METADATA_STAGE))
        self.assertEqual(json['name'], 'Unnamed')
        self.assertEqual(json['description'], 'No description')
        self.assertEqual(json['stage'], 'No stage')

    def test_list_stages_require_plan(self):
        json = self.get_stages()[REQUIRED_PLAN_STAGE - 1]
        self.assertEqual(json['uuid'], str(REQUIRED_PLAN_STAGE))
        self.assertEqual(json['status'], 'requires_plan_id')

    def test_list_stages_not_require_plan(self):
        json = self.get_stages()[NO_REQUIRED_PLAN_STAGE - 1]
        self.assertEqual(json['uuid'], str(NO_REQUIRED_PLAN_STAGE))
        self.assertEqual(json['status'], 'new')

    def test_stages_contain_full_validations(self):
        for stage in self.get_stages():
            for validation in stage['validations']:
                self.validate_generic_validation(validation)

    def test_get_stage(self):
        rv = self.app.get('/v1/stages/{}/'.format(VALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.json_response(rv)

    def test_get_unknown_stage(self):
        rv = self.app.get('/v1/stages/{}/'.format(INVALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.json_response(rv, 404)

    def test_get_stage_with_unknown_plan(self):
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.get('/v1/stages/{}/?plan_id=invalid'
                              .format(VALID_UUID))
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    def test_get_new_stage_no_plan_content(self):
        rv = self.app.get('/v1/stages/{}/'.format(NO_REQUIRED_PLAN_STAGE))
        self.assertDictContainsSubset(
            {
                'uuid': str(NO_REQUIRED_PLAN_STAGE),
                'status': 'new',
            }, self.json_response(rv)['stage'])

    def test_stage_run(self):
        with mock.patch(VALIDATION_RUN_METHOD) as validation_run_mock:
            validation_run_mock.side_effect = passing_validation
            rv = self.app.put('/v1/stages/{}/run'
                              .format(NO_REQUIRED_PLAN_STAGE))
            self.assertEqual(rv.status_code, 204)
            wait_for_request_to_be_processed()
            self.assertEqual(validation_run_mock.call_count, 1)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_stage_run_with_plan(self, get_plan_mock):
        get_plan_mock.return_value = True
        with mock.patch(VALIDATION_RUN_METHOD) as validation_run_mock:
            validation_run_mock.side_effect = passing_validation
            rv = self.app.put('/v1/stages/{}/run?plan_id=plan1'
                              .format(MIXED_STAGE))
            self.assertEqual(rv.status_code, 204)
            wait_for_request_to_be_processed()
            # Note this stage has 2 validations
            self.assertEqual(validation_run_mock.call_count, 2)

    def test_run_unknown_stage(self):
        rv = self.app.put('/v1/stages/{}/run'.format(INVALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.json_response(rv, 404)

    def test_run_stage_with_unknown_plan(self):
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.put('/v1/stages/{}/run?plan_id=invalid'
                              .format(VALID_UUID))
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    def test_get_running_stage_content(self):
        self.run_stage(NO_REQUIRED_PLAN_STAGE, running_validation)
        stage = self.get_stage(NO_REQUIRED_PLAN_STAGE)
        self.validate_running_stage(stage)
        self.assertEqual(str(NO_REQUIRED_PLAN_STAGE), stage['uuid'])

    def test_get_successful_stage_content(self):
        self.run_stage(NO_REQUIRED_PLAN_STAGE, passing_validation)
        stage = self.get_stage(NO_REQUIRED_PLAN_STAGE)
        self.validate_successful_stage(stage)
        self.assertEqual(str(NO_REQUIRED_PLAN_STAGE), stage['uuid'])

    def test_get_failed_stage_content(self):
        self.run_stage(NO_REQUIRED_PLAN_STAGE, failing_validation)
        stage = self.get_stage(NO_REQUIRED_PLAN_STAGE)
        self.validate_failing_stage(stage)
        self.assertEqual(str(NO_REQUIRED_PLAN_STAGE), stage['uuid'])

    def test_reject_stage_missing_plan(self):
        with mock.patch(VALIDATION_RUN_METHOD) as validation_run_mock:
            validation_run_mock.side_effect = passing_validation
            rv = self.app.put('/v1/stages/{}/run'.format(REQUIRED_PLAN_STAGE))
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    def test_stage_stop_running(self):
        self.run_stage(NO_REQUIRED_PLAN_STAGE, running_validation)

        rv = self.app.put('/v1/stages/{}/stop'.format(NO_REQUIRED_PLAN_STAGE))
        self.assertEqual(rv.status_code, 204)

        stage = self.get_stage(NO_REQUIRED_PLAN_STAGE)
        self.validate_canceled_stage(stage)
        self.assertEqual(str(NO_REQUIRED_PLAN_STAGE), stage['uuid'])

    def test_stage_stop_unknown(self):
        rv = self.app.put('/v1/stages/{}/stop'.format(INVALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 404)

    def test_stage_stop_with_unknown_plan(self):
        self.run_stage(REQUIRED_PLAN_STAGE,
                       running_validation, plan_id='plan1')
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.put('/v1/stages/{}/stop?plan_id=invalid'
                              .format(REQUIRED_PLAN_STAGE))
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_stage_stop_with_plan_id(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_stage(REQUIRED_PLAN_STAGE,
                       running_validation, plan_id='plan1')
        rv = self.app.put('/v1/stages/{}/stop?plan_id=plan1'
                          .format(REQUIRED_PLAN_STAGE))
        self.assertEqual(rv.status_code, 204)

        stage = self.get_stage(REQUIRED_PLAN_STAGE, plan_id='plan1')
        self.validate_canceled_stage(stage)
        self.assertEqual(str(REQUIRED_PLAN_STAGE), stage['uuid'])

    def test_stage_stop_missing_plan_id(self):
        self.run_stage(REQUIRED_PLAN_STAGE,
                       running_validation, plan_id='plan1')
        rv = self.app.put('/v1/stages/{}/stop'.format(REQUIRED_PLAN_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 404)

    def test_stage_rerun_running(self):
        self.run_stage(NO_REQUIRED_PLAN_STAGE, running_validation)

        rv = self.app.put('/v1/stages/{}/run'.format(NO_REQUIRED_PLAN_STAGE))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 400)

        stage = self.get_stage(NO_REQUIRED_PLAN_STAGE)
        self.validate_running_stage(stage)
        self.assertEqual(str(NO_REQUIRED_PLAN_STAGE), stage['uuid'])

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_stage_rerun_running_with_plan(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_stage(REQUIRED_PLAN_STAGE,
                       running_validation, plan_id='plan_1')

        rv = self.app.put('/v1/stages/{}/run?plan_id=plan_1'
                          .format(REQUIRED_PLAN_STAGE))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 400)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_filter_stage_results(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_stage(REQUIRED_PLAN_STAGE,
                       passing_validation, plan_id='plan1')
        self.run_stage(REQUIRED_PLAN_STAGE,
                       failing_validation, plan_id='plan2')
        stage_plan1 = self.get_stage(REQUIRED_PLAN_STAGE, plan_id='plan1')
        stage_plan2 = self.get_stage(REQUIRED_PLAN_STAGE, plan_id='plan2')

        self.validate_stage_with_plan(stage_plan1, 'plan1')
        self.validate_stage_with_plan(stage_plan2, 'plan2')
        self.validate_successful_stage(stage_plan1)
        self.validate_failing_stage(stage_plan2)

    def test_stage_require_plan_status(self):
        self.run_stage(REQUIRED_PLAN_STAGE,
                       passing_validation, plan_id='plan1')
        stage_no_plan = self.get_stage(REQUIRED_PLAN_STAGE)
        self.validate_stage_with_plan_missing_plan_id(stage_no_plan)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_filter_stages_results(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_stage(REQUIRED_PLAN_STAGE,
                       passing_validation, plan_id='plan1')
        self.run_stage(REQUIRED_PLAN_STAGE,
                       failing_validation, plan_id='plan2')

        stage_plan1 = next(s for s in self.get_stages(plan_id='plan1')
                           if s['uuid'] == str(REQUIRED_PLAN_STAGE))
        stage_plan2 = next(s for s in self.get_stages(plan_id='plan2')
                           if s['uuid'] == str(REQUIRED_PLAN_STAGE))
        stage_no_plan = next(s for s in self.get_stages()
                             if s['uuid'] == str(REQUIRED_PLAN_STAGE))

        self.validate_stage_with_plan(stage_plan1, 'plan1')
        self.validate_stage_with_plan(stage_plan2, 'plan2')
        self.validate_successful_stage(stage_plan1)
        self.validate_failing_stage(stage_plan2)
        self.validate_stage_with_plan_missing_plan_id(stage_no_plan)

    ########
    # Validation results
    ########

    def test_list_validation_results_empty(self):
        results = self.get_results()
        self.assertEqual(len(results), 0)

    def test_list_validation_results(self):
        self.run_validation(VALID_UUID, running_validation)
        results = self.get_results()
        self.assertEqual(len(results), 1)

    def test_list_validation_results_with_unknown_plan(self):
        with mock.patch(GET_PLAN_METHOD) as get_plan_mock:
            get_plan_mock.side_effect = swiftexceptions.ClientException(
                "test-error", http_status=404)
            rv = self.app.get('/v1/validation_results/?plan_id=invalid')
            self.assertEqual(rv.content_type, 'application/json')
            self.assertEqual(rv.status_code, 404)

    def test_unknown_validation_result(self):
        rv = self.app.get('/v1/validation_results/{}/'.format(INVALID_UUID))
        self.assertEqual(rv.content_type, 'application/json')
        self.assertEqual(rv.status_code, 404)

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_validation_for_plan(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_validation(VALID_UUID, passing_validation, plan_id='plan1')
        result = self.get_results()[0]
        self.validate_successful_result(result)
        self.assertEqual(result['plan_id'], 'plan1')

    @mock.patch('tripleo_common.core.plan_storage.SwiftPlanStorageBackend.get')
    def test_filter_list_validation_results(self, get_plan_mock):
        get_plan_mock.return_value = True
        self.run_validation(REQUIRED_PLAN_UUID,
                            passing_validation, plan_id='plan1')
        self.run_validation(REQUIRED_PLAN_UUID,
                            failing_validation, plan_id='plan2')

        results_plan1 = self.get_results(plan_id='plan1')
        results_plan2 = self.get_results(plan_id='plan2')
        results_no_plan = self.get_results()

        self.assertEqual(len(results_plan1), 1)
        self.assertEqual(len(results_plan2), 1)
        self.assertEqual(len(results_no_plan), 2)
