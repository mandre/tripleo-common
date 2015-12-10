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

from oslo_config import cfg

from tripleo_common.api import main
from tripleo_common.tests import base

CONF = cfg.CONF


class BaseAPITest(base.TestCase):

    def setUp(self):
        super(BaseAPITest, self).setUp()
        CONF([], project='tripleo-common')
        app = main.create_app()
        app.config['TESTING'] = True
        self.app = app.test_client()
        CONF.set_override('auth_strategy', 'noauth')

    def assertJSONEquals(self, expected, json_string):
        parsed_json = json.loads(json_string.decode('utf-8'))
        self.assertEqual(expected, parsed_json)


class APIMainTestCase(BaseAPITest):

    def test_root(self):
        res = self.app.get('/')
        self.assertEqual(200, res.status_code)

        self.assertJSONEquals({
            'versions': [{
                'id': '1.0',
                'links': [{
                    'href': 'http://localhost/v1', 'rel': 'self'
                }],
                'status': 'CURRENT'
            }]
        }, res.data)

    def test_invalid_version(self):

        res = self.app.get('/', headers={
            'X-OpenStack-TripleO-API-Version': "0.0"
        })
        self.assertEqual(406, res.status_code)
        self.assertJSONEquals({
            'error': {
                'message': (
                    'Unsupported API version 0.0, supported range is 1.0 '
                    'to 1.0'
                )
            }
        }, res.data)

    def test_malformed_version(self):

        res = self.app.get('/', headers={
            'X-OpenStack-TripleO-API-Version': "version 1.0"
        })
        self.assertEqual(400, res.status_code)
        self.assertJSONEquals({
            'error': {
                'message': (
                    'Malformed API version: expected string in form of X.Y'
                )
            }
        }, res.data)

    def test_version_root_missing(self):

        res = self.app.get('/0')
        self.assertJSONEquals({
            'error': {
                'message': 'Version not found.'
            }
        }, res.data)
        self.assertEqual(404, res.status_code)

    def test_404_handler(self):

        res = self.app.get('/INVALID/PATH/')
        self.assertEqual(404, res.status_code)
        self.assertJSONEquals({
            'error': {
                'message': '404: Not Found'
            }
        }, res.data)
