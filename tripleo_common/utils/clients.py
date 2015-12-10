# Copyright 2013 Red Hat
# All Rights Reserved.

#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


#    Most of the following was copied shamelessly from nova @
#    https://github.com/openstack/nova/blob/master/nova/image/glance.py
#    It's the way nova talks to glance, though obviously
#    s/python-glanceclient/python-novaclient


"""A client library for accessing OpenStack APIs using Boto"""

from oslo_config import cfg
from oslo_log import log

from heatclient.v1.client import Client as heat_client
from keystoneclient.v2_0 import client as ksclient
from swiftclient import client as swift_client

from tripleo_common.core.i18n import _LE


HEAT_OPTS = [
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               help='Heat API service endpoint type in keystone'
               )
]

KEYSTONE_OPTS = [
    cfg.StrOpt('username',
               default='admin',
               help='The name of a user the overcloud is deployed on behalf of'
               ),
    cfg.StrOpt('password',
               help='The pass of a user the overcloud is deployed on behalf of'
               ),
    cfg.StrOpt('tenant_name',
               default='admin',
               help='The tenant name the overcloud is deployed on behalf of'
               ),
    cfg.StrOpt('auth_url',
               default='http://localhost:35357/v2.0',
               help='Keystone authentication URL'),
    cfg.StrOpt('auth_version',
               default='2',
               help='Keystone authentication API version'),
    cfg.BoolOpt('insecure',
                default=True,
                help='Set to False when Heat API uses HTTPS'
                )
]

SWIFT_OPTS = [
    cfg.IntOpt('max_retries',
               default=2,
               help='Maximum number of times to retry a Swift request, '
                    'before failing.'),
    cfg.StrOpt('os_endpoint_type',
               default='internalURL',
               help='Swift endpoint type.'),
]


CONF = cfg.CONF
CONF.register_opts(HEAT_OPTS, group='heat')
CONF.register_opts(KEYSTONE_OPTS, group='keystone')
CONF.register_opts(SWIFT_OPTS, group='swift')
LOG = log.getLogger(__name__)


def list_opts():
    return [
        ('heat', HEAT_OPTS),
        ('keystone', KEYSTONE_OPTS),
        ('swift', SWIFT_OPTS),
    ]


def heatclient():
    try:
        keystone = ksclient.Client(**CONF.keystone)
        endpoint = keystone.service_catalog.url_for(
            service_type='orchestration',
            endpoint_type=CONF.heat['endpoint_type']
        )
        return heat_client(
            endpoint=endpoint,
            token=keystone.auth_token,
            username=CONF.keystone['username'],
            password=CONF.keystone['password'])
    except Exception:
        LOG.exception(_LE("An error occurred initializing the Heat client"))


def swiftclient():
    try:
        params = {'retries': CONF.swift.max_retries,
                  'user': CONF.keystone.username,
                  'tenant_name': CONF.keystone.tenant_name,
                  'key': CONF.keystone.password,
                  'authurl': CONF.keystone.auth_url,
                  'auth_version': CONF.keystone.auth_version,
                  'os_options': {'service_type': 'object-store',
                                 'endpoint_type': CONF.swift.os_endpoint_type}}

        return swift_client.Connection(**params)
    except Exception:
        LOG.exception(_LE("An error occurred initializing the Swift client"))
