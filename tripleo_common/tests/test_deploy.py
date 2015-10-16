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

import mock
import os
import tempfile

from tripleo_common import deploy
from tripleo_common.tests import base


class DeployManagerTest(base.TestCase):

    def setUp(self):
        super(DeployManagerTest, self).setUp()

        self.heatclient = mock.MagicMock()
        self.heatclient.stacks.get.return_value = None
        self.deploy_manager = deploy.DeployManager(self.heatclient)

    def test_deploy_create(self):

        self.deploy_manager.deploy("template", {}, {})

        self.heatclient.stacks.create.assert_called_once_with(
            environment={},
            files={},
            stack_name=None,
            template='template',
            timeout_mins=420,
        )


class FileDeployManagerTest(base.TestCase):

    def setUp(self):
        super(FileDeployManagerTest, self).setUp()

        self.heatclient = mock.MagicMock()
        self.heatclient.stacks.get.return_value = None
        self.deploy_manager = deploy.FileDeployManager(self.heatclient)

        self.env1 = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.env2 = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.template = tempfile.NamedTemporaryFile(mode='w', delete=False)

        self.template.write("heat_template_version: 2015-04-30\n\n")
        self.template.write("description: Simple")
        self.template.close()

    def tearDown(self):
        super(FileDeployManagerTest, self).tearDown()

        os.unlink(self.env1.name)
        os.unlink(self.env2.name)
        os.unlink(self.template.name)

    def test_deploy_create(self):

        self.deploy_manager.deploy(
            self.template.name,
            [self.env1.name, self.env2.name],
            {'param1': 1, 'param2': 2})

        self.heatclient.stacks.create.assert_called_once_with(
            environment={},
            files={},
            parameters={'param2': 2, 'param1': 1},
            stack_name=None,
            template={
                'description': 'Simple',
                'heat_template_version': '2015-04-30'
            },
            timeout_mins=420,
        )
