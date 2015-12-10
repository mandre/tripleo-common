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

from oslo_config import cfg


SERVICE_OPTS = [
    cfg.StrOpt('listen_address',
               default='0.0.0.0',
               help='IP to listen on'),
    cfg.IntOpt('listen_port',
               default=8585,
               help='Port to listen on.'),
    cfg.StrOpt('auth_strategy',
               default='keystone',
               choices=('keystone', 'noauth'),
               help='Authentication method used on the TripleO API.  Either '
                    '"noauth" or "keystone" are currently valid options.  '
                    '"noauth" will disable all authentication.'),
    cfg.BoolOpt('authenticate',
                default=None,
                help='DEPRECATED: use auth_strategy.',
                deprecated_for_removal=True),
    cfg.BoolOpt('use_ssl',
                default=False,
                help='SSL Enabled/Disabled'),
    cfg.StrOpt('ssl_cert_path',
               default='',
               help='Path to SSL certificate'),
    cfg.StrOpt('ssl_key_path',
               default='',
               help='Path to SSL key'),
    cfg.IntOpt('max_concurrency',
               default=1000,
               help='The green thread pool size.'),
]


cfg.CONF.register_opts(SERVICE_OPTS)


def list_opts():
    return [
        ('', SERVICE_OPTS),
    ]
