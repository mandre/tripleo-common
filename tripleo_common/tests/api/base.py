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
import os
import tempfile

from oslo_config import cfg

from tripleo_common.api import database
from tripleo_common.api import main
from tripleo_common.core import validation_manager
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
        CONF.set_override('validations_base_dir', 'tripleo_common/tests/api')
        self.db_fd, db_path = tempfile.mkstemp()
        CONF.set_override('validations_database', db_path)
        validation_manager.prepare_database()
        database.init_db()

    def tearDown(self):
        super(BaseAPITest, self).tearDown()
        os.close(self.db_fd)
        os.unlink(CONF.validations_database)

    def assertJSONEquals(self, expected, json_string):
        parsed_json = json.loads(json_string.decode('utf-8'))
        self.assertEqual(expected, parsed_json)
