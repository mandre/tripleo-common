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

import flask
import threading

from tripleo_common.api import utils
from tripleo_common.core import plan
from tripleo_common.core import plan_storage
from tripleo_common.utils import clients

v1 = flask.Blueprint('V1', __name__)


def _plan_manager():
    swift_backend = plan_storage.SwiftPlanStorageBackend(clients.swiftclient())
    return plan.PlanManager(swift_backend, clients.heatclient())


@v1.route('/plans', methods=['GET', 'POST'])
@utils.convert_exceptions
def api_plans():
    utils.check_auth(flask.request)

    plan_manager = _plan_manager()

    if flask.request.method == 'GET':
        plan_names = plan_manager.get_plan_list()
        plans = []
        for name in plan_names:
            plan = {
                'name': name,
                'links': utils.plan_link_object(name),
            }
            plans.append(plan)
        return flask.jsonify(plans=plans)
    else:
        body = flask.request.get_json(force=True)
        plan = plan_manager.create_plan(body['name'], body['files'])
        return flask.jsonify(plan=utils.plan_repr(plan))


@v1.route('/plans/<name>', methods=['GET', 'DELETE', 'PATCH'])
@utils.convert_exceptions
def api_plan(name):
    utils.check_auth(flask.request)

    plan_manager = _plan_manager()

    if flask.request.method == 'GET':
        plan = plan_manager.get_plan(name)
        return flask.jsonify(plan=utils.plan_repr(plan))
    elif flask.request.method == 'DELETE':
        plan_manager.delete_plan(name)
        return '', 204
    else:
        body = flask.request.get_json(force=True)
        plan = plan_manager.update_plan(name, body['files'])
        return flask.jsonify(plan=utils.plan_repr(plan))


@v1.route('/plans/<name>/environments', methods=['GET', 'PATCH'])
@utils.convert_exceptions
def api_plan_environments(name):
    utils.check_auth(flask.request)
    plan_manager = _plan_manager()

    if flask.request.method == 'GET':
        environments = plan_manager.get_deployment_plan_environments(name)
    else:
        body = flask.request.get_json(force=True)
        plan_manager.update_deployment_plan_environments(name, body)
        environments = plan_manager.get_deployment_plan_environments(name)
    return flask.jsonify(environments=environments)


@v1.route('/plans/<name>/parameters', methods=['GET', 'PATCH'])
@utils.convert_exceptions
def api_plan_parameters(name):
    utils.check_auth(flask.request)
    plan_manager = _plan_manager()

    if flask.request.method == 'GET':
        parameters = plan_manager.get_deployment_parameters(name)
    else:
        body = flask.request.get_json(force=True)
        plan_manager.update_deployment_parameters(name, body)
        parameters = plan_manager.get_deployment_parameters(name)
    return flask.jsonify(parameters=parameters)


@v1.route('/validations/')
def list_validations():
    result = [utils.formatted_validation(validation)
              for validation in utils.db_validations().values()]
    return utils.json_response(200, result)


@v1.route('/validations/<validation_id>/')
def show_validation(validation_id):
    try:
        validation = utils.db_validations()[validation_id]
    except KeyError:
        return utils.json_response(404, {})
    return utils.json_response(200, utils.formatted_validation(validation))


@v1.route('/validations/<validation_id>/run', methods=['PUT'])
def run_validation(validation_id):
    try:
        validation = utils.db_validations()[validation_id]
    except KeyError:
        return utils.json_response(404, {'error': "validation not found"})

    previous_thread = validation['current_thread']
    if previous_thread and previous_thread.is_alive():
        return utils.json_response(400, {'error': "validation already running"})

    validation_url = flask.url_for('V1.show_validation', validation_id=validation_id)
    cancel_event = threading.Event()
    validation_arguments = {
        'plan_id': flask.request.args.get('plan_id'),
    }
    thread = threading.Thread(
        target=utils.thread_run_validation,
        args=(validation, validation_url, cancel_event, validation_arguments))
    thread.cancel_event = cancel_event
    validation['current_thread'] = thread
    thread.start()
    return utils.json_response(204, {})


@v1.route('/validations/<validation_id>/stop', methods=['PUT'])
def stop_validation(validation_id):
    try:
        validation = utils.db_validations()[validation_id]
    except KeyError:
        return utils.json_response(404, {'error': "validation not found"})
    thread = validation['current_thread']
    if thread and thread.is_alive():
        validation['results'].values()[-1]['status'] = 'canceled'
        thread.cancel_event.set()
        return utils.json_response(204, {})
    else:
        return utils.json_response(400, {'error': "validation is not running"})


@v1.route('/stages/')
def list_stages():
    stages = utils.db()['types'].values()
    result = []
    for stage in stages:
        result.append(utils.formatted_stage(stage))
    return utils.json_response(200, result)


@v1.route('/stages/<stage_id>/')
def show_stage(stage_id):
    try:
        stage = utils.db()['types'][stage_id]
    except KeyError:
        return utils.json_response(404, {})
    return utils.json_response(200, utils.formatted_stage(stage))


@v1.route('/stages/<stage_id>/run', methods=['PUT'])
def run_stage(stage_id):
    try:
        stage = utils.db()['types'][stage_id]
    except KeyError:
        return utils.json_response(404, {})
    for validation in stage['validations'].values():
        validation_url = flask.url_for('V1.show_validation', validation_id=validation['uuid'])
        validation_arguments = {
            'plan_id': flask.request.args.get('plan_id'),
        }
        thread = threading.Thread(
            target=utils.thread_run_validation,
            args=(validation, validation_url, None, validation_arguments))
        thread.start()
    return utils.json_response(204, {})


@v1.route('/results/')
def list_results():
    all_results = []
    for validation in utils.db_validations().values():
        all_results.extend(validation['results'].values())
    all_results.sort(key=lambda x: x['date'])
    return utils.json_response(200, all_results)


@v1.route('/results/<result_id>/')
def show_result(result_id):
    for validation in utils.db_validations().values():
        for result in validation.get('results', {}).values():
            if result['uuid'] == result_id:
                return utils.json_response(200, result)
    return utils.json_response(404, {})
