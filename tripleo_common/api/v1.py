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

from tripleo_common.api import utils
from tripleo_common.core import plan
from tripleo_common.core import plan_storage
from tripleo_common.core import validation_manager
from tripleo_common.core import validation_result
from tripleo_common.utils import clients

v1 = flask.Blueprint('V1', __name__)


def _plan_manager():
    swift_backend = plan_storage.SwiftPlanStorageBackend(clients.swiftclient())
    return plan.PlanManager(swift_backend, clients.heatclient())


def _plan_id_from_param():
    plan_id = flask.request.args.get('plan_id')
    if plan_id:
        # Make sure the plan exists
        _plan_manager().get_plan(plan_id)
    return plan_id


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
    plan_id = _plan_id_from_param()
    validations = [utils.validation_repr(validation, plan_id=plan_id)
                   for validation in validation_manager.get_all_validations()]
    return flask.jsonify(validations=validations)


@v1.route('/validations/<validation_id>/')
def show_validation(validation_id):
    plan_id = _plan_id_from_param()
    validation = validation_manager.get_validation(validation_id)
    return flask.jsonify(
        validation=utils.validation_repr(validation, plan_id=plan_id))


@v1.route('/validations/<validation_id>/run', methods=['PUT'])
def run_validation(validation_id):
    validation = validation_manager.get_validation(validation_id)
    validation.run(_plan_id_from_param())
    return '', 204


@v1.route('/validations/<validation_id>/stop', methods=['PUT'])
def stop_validation(validation_id):
    validation = validation_manager.get_validation(validation_id)
    validation.stop(_plan_id_from_param())
    return '', 204


@v1.route('/stages/')
def list_stages():
    plan_id = _plan_id_from_param()
    stages = [utils.stage_repr(stage, plan_id=plan_id)
              for stage in validation_manager.get_all_stages()]
    return flask.jsonify(stages=stages)


@v1.route('/stages/<stage_id>/')
def show_stage(stage_id):
    plan_id = _plan_id_from_param()
    stage = validation_manager.get_stage(stage_id)
    return flask.jsonify(stage=utils.stage_repr(stage, plan_id=plan_id))


@v1.route('/stages/<stage_id>/run', methods=['PUT'])
def run_stage(stage_id):
    stage = validation_manager.get_stage(stage_id)
    stage.run(_plan_id_from_param())
    return '', 204


@v1.route('/stages/<stage_id>/stop', methods=['PUT'])
def stop_stage(stage_id):
    stage = validation_manager.get_stage(stage_id)
    stage.stop(_plan_id_from_param())
    return '', 204


@v1.route('/validation_results/')
def list_results():
    plan_id = _plan_id_from_param()
    all_results = [utils.result_repr(result)
                   for result in validation_result.get_all_results(plan_id)]
    return flask.jsonify(results=all_results)


@v1.route('/validation_results/<result_id>/')
def show_result(result_id):
    result = validation_result.get_results([result_id])[-1]
    return flask.jsonify(result=utils.result_repr(result))
