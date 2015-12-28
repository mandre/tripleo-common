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
import functools
import os
import ssl
import sys
import uuid

import flask
import werkzeug

from oslo_config import cfg
from oslo_log import log

from tripleo_common.core import exception
from tripleo_common.core import validations
from tripleo_common.core.i18n import _LE
from tripleo_common.core.i18n import _LW


CONF = cfg.CONF
LOG = log.getLogger('tripleo_common.api.utils')


def create_link_object(urls):
    links = []
    for url in urls:
        links.append({"rel": "self",
                      "href": os.path.join(flask.request.url_root, url)})
    return links


def generate_resource_data(resources):
    data = []
    for resource in resources:
        item = {}
        item['name'] = str(resource).split('/')[-1]
        item['links'] = create_link_object([str(resource)[1:]])
        data.append(item)
    return data


def plan_link_object(name):
    return create_link_object([flask.url_for('V1.api_plan', name=name)])


def plan_repr(plan):
    return {
        'name': plan.name,
        'files': plan.files,
        'metadata': plan.metadata,
        'links': plan_link_object(plan.name)
    }


def check_auth(request):
    """Check authentication on request.

    :param request: Flask request
    :raises: Error if access is denied
    """
    if get_auth_strategy() == 'noauth':
        return
    if request.headers.get('X-Identity-Status').lower() == 'invalid':
        raise exception.AuthenticationRequiredError()
    roles = (request.headers.get('X-Roles') or '').split(',')
    if 'admin' not in roles:
        LOG.error(_LE('Role "admin" not in user role list %s'), roles)
        raise exception.AccessDeniedError()


def get_auth_strategy():
    if CONF.authenticate is not None:
        return 'keystone' if CONF.authenticate else 'noauth'
    return CONF.auth_strategy


def create_ssl_context():
    if not CONF.use_ssl:
        return

    MIN_VERSION = (2, 7, 9)

    if sys.version_info < MIN_VERSION:
        LOG.warning(_LW('Unable to use SSL in this version of Python: '
                        '%{current}, please ensure your version of Python is '
                        'greater than %{min} to enable this feature.'),
                    {'current': '.'.join(map(str, sys.version_info[:3])),
                     'min': '.'.join(map(str, MIN_VERSION))})
        return

    context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    if CONF.ssl_cert_path and CONF.ssl_key_path:
        try:
            context.load_cert_chain(CONF.ssl_cert_path, CONF.ssl_key_path)
        except IOError as exc:
            LOG.warning(_LW('Failed to load certificate or key from defined '
                            'locations: %{cert} and %{key}, will continue to '
                            'run with the default settings: %{exc}'),
                        {'cert': CONF.ssl_cert_path, 'key': CONF.ssl_key_path,
                         'exc': exc})
        except ssl.SSLError as exc:
            LOG.warning(_LW('There was a problem with the loaded certificate '
                            'and key, will continue to run with the default '
                            'settings: %s'), exc)
    return context


def convert_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exception.TripleoCommonException as exc:
            return error_response(exc, exc.status_code)
        except werkzeug.exceptions.HTTPException as exc:
            return error_response(exc, exc.code or 400)
        except Exception as exc:
            LOG.exception(_LE('Internal server error'))
            return error_response(exc)

    return wrapper


def error_response(exc, code=500):
    res = flask.jsonify(error={'message': str(exc)})
    res.status_code = code
    LOG.debug('Returning error to client: %s', exc)
    return res


# TODO(mandre) find a better place for DB
DB = {
    'validations': {},
    'types': {},
}
DB_VALIDATIONS = DB['validations']  # TODO: OMG THREAD SAFETY

def db():
    return DB

def db_validations():
    return DB_VALIDATIONS

def prepare_database():
    all_validations = validations.get_all_validations().values()
    all_stages = validations.get_all_stages().values()
    for validation in all_validations:
        validation['results'] = {}
        validation['current_thread'] = None
        DB_VALIDATIONS[validation['uuid']] = validation
    for stage in all_stages:
        included_validations = {}
        for loaded_validation in stage['validations']:
            validation_id = loaded_validation['uuid']
            # XXX(mandre) we want a reference and not a copy
            included_validations[validation_id] = DB_VALIDATIONS[validation_id]
        stage['validations'] = included_validations
        DB['types'][stage['uuid']] = stage


def thread_run_validation(validation, validation_url, cancel_event, arguments):
    global DB_VALIDATIONS
    results = DB_VALIDATIONS[validation['uuid']]['results']

    result_id = str(uuid.uuid4())
    # TODO: proper datetime formatting
    result_start_time = datetime.datetime.utcnow().isoformat() + 'Z'
    new_result = {
        'uuid': result_id,
        'date': result_start_time,
        'validation': validation_url,
        'status': 'running',
        'arguments': arguments,
    }
    results[result_id] = new_result

    validation_run_result = validations.run(validation, cancel_event)

    results[result_id]['detailed_description'] = validation_run_result
    success = all((result.get('success') for result in validation_run_result.values()))
    if success:
        results[result_id]['status'] = 'success'
    else:
        results[result_id]['status'] = 'failed'


def json_response(code, result):
    # NOTE: flask.jsonify doesn't handle lists, so we need to do it manually:
    response = flask.make_response(flask.json.dumps(result), code)
    response.headers['Content-Type'] = 'application/json'
    response.code = code
    return response


def formatted_validation(validation):
    results = validation['results']
    sorted_results = sorted(results.values(), key=lambda r: r['date'])
    if sorted_results:
        latest_result = sorted_results[-1]
    else:
        latest_result = None
    return {
        'uuid': validation['uuid'],
        'name': validation['name'],
        'description': validation['description'],
        'ref': flask.url_for('V1.show_validation', validation_id=validation['uuid']),
        'status': validation_status(validation),
        'latest_result': latest_result,
        'results': [flask.url_for('V1.show_result', result_id=r['uuid'])
                    for r in sorted_results],
    }

def formatted_stage(stage):
    formatted_validations = [formatted_validation(validation)
                             for validation in stage['validations'].values()]
    return {
        'uuid': stage['uuid'],
        'ref': flask.url_for('V1.show_stage', stage_id=stage['uuid']),
        'name': stage['name'],
        'description': stage['description'],
        'stage': stage['stage'],
        'status': aggregate_status(stage),
        'validations': formatted_validations,
    }


def validation_status(validation):
    sorted_results = sorted(validation['results'].values(), key=lambda r: r['date'])
    if sorted_results:
        return sorted_results[-1].get('status', 'new')
    else:
        return 'new'

def aggregate_status(stage):
    all_statuses = [validation_status(k) for k in stage['validations'].values()]
    if all(status == 'new' for status in all_statuses):
        return 'new'
    elif all(status == 'success' for status in all_statuses):
        return 'success'
    elif any(status == 'canceled' for status in all_statuses):
        return 'canceled'
    elif any(status == 'failed' for status in all_statuses):
        return 'failed'
    elif any(status == 'running' for status in all_statuses):
        return 'running'
    else:
        # Should never happen
        return 'unknown'
