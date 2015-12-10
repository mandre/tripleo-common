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
