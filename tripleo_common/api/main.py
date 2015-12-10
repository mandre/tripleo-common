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

import re
import sys

import flask
from keystonemiddleware import auth_token
from oslo_config import cfg
from oslo_log import log
from oslo_middleware import cors

from tripleo_common.api import utils
from tripleo_common import conf  # noqa
from tripleo_common.core import exception
from tripleo_common.core.i18n import _
from tripleo_common.core.i18n import _LW


CONF = cfg.CONF
LOG = log.getLogger('tripleo_common.api.main')

MINIMUM_API_VERSION = (1, 0)
CURRENT_API_VERSION = (1, 0)
_MIN_VERSION_HEADER = 'X-OpenStack-TripleO-API-Minimum-Version'
_MAX_VERSION_HEADER = 'X-OpenStack-TripleO-API-Maximum-Version'
_VERSION_HEADER = 'X-OpenStack-TripleO-API-Version'


def _format_version(ver):
    return '%d.%d' % ver

_DEFAULT_API_VERSION = _format_version(MINIMUM_API_VERSION)


def create_app():

    app = flask.Flask(__name__)

    @app.before_request
    def check_api_version():
        requested = flask.request.headers.get(_VERSION_HEADER,
                                              _DEFAULT_API_VERSION)
        try:
            requested = tuple(int(x) for x in requested.split('.'))
        except (ValueError, TypeError):
            return utils.error_response(_('Malformed API version: expected '
                                          'string in form of X.Y'), code=400)

        if requested < MINIMUM_API_VERSION or requested > CURRENT_API_VERSION:
            return utils.error_response(
                _('Unsupported API version %(requested)s, '
                  'supported range is %(min)s to %(max)s') %
                {'requested': _format_version(requested),
                 'min': _format_version(MINIMUM_API_VERSION),
                 'max': _format_version(CURRENT_API_VERSION)}, code=406)

    @app.after_request
    def add_version_headers(res):
        res.headers[_MIN_VERSION_HEADER] = '%s.%s' % MINIMUM_API_VERSION
        res.headers[_MAX_VERSION_HEADER] = '%s.%s' % CURRENT_API_VERSION
        return res

    @app.route('/', methods=['GET'])
    @utils.convert_exceptions
    def api_root():
        versions = [
            {
                "status": "CURRENT",
                "id": '%s.%s' % CURRENT_API_VERSION,
            },
        ]

        for version in versions:
            version['links'] = utils.create_link_object(
                ["v%s" % version['id'].split('.')[0]])

        return flask.jsonify(versions=versions)

    @app.route('/<version>', methods=['GET'])
    @utils.convert_exceptions
    def version_root(version):
        pat = re.compile("^\/%s\/[^\/]*?$" % version)

        resources = []
        for url in app.url_map.iter_rules():
            if pat.match(str(url)):
                resources.append(url)

        if not resources:
            raise exception.VersionNotFoundError()

        return flask.jsonify(resources=utils.generate_resource_data(resources))

    @app.errorhandler(404)
    def handle_404(error):
        return utils.error_response(error, code=404)

    @app.errorhandler(exception.TripleoCommonException)
    def handle_invalid_usage(error):
        response = flask.jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    app.wsgi_app = cors.CORS(app.wsgi_app, cfg.CONF)

    if utils.get_auth_strategy() != 'noauth':
        auth_conf = dict(CONF.keystone_authtoken)
        auth_conf.update({
            'admin_password': CONF.keystone_authtoken.admin_password,
            'admin_user': CONF.keystone_authtoken.admin_user,
            'auth_uri': CONF.keystone_authtoken.auth_uri,
            'admin_tenant_name': CONF.keystone_authtoken.admin_tenant_name,
            'identity_uri': CONF.keystone_authtoken.identity_uri
        })
        auth_conf['delay_auth_decision'] = True
        app.wsgi_app = auth_token.AuthProtocol(app.wsgi_app, auth_conf)
    else:
        LOG.warning(_LW('Starting unauthenticated, please check'
                        ' configuration'))
    return app


def main(args=sys.argv[1:]):  # pragma: no cover

    log.register_options(CONF)
    CONF(args, project='tripleo-common')

    log.set_defaults(default_log_levels=[
        'urllib3.connectionpool=WARN',
        'keystonemiddleware.auth_token=WARN',
        'requests.packages.urllib3.connectionpool=WARN'])
    log.setup(CONF, 'tripleo_common')

    app_kwargs = {'host': CONF.listen_address,
                  'port': CONF.listen_port}

    context = utils.create_ssl_context()
    if context:
        app_kwargs['ssl_context'] = context

    app = create_app()

    app.run(**app_kwargs)


if __name__ == '__main__':
    main()
