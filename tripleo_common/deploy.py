# Copyright 2015 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from heatclient.common import template_utils

from tripleo_common import utils


LOG = logging.getLogger(__name__)


class DeployManager(object):
    """A manager to handle deploying to Heat.

    The intended usage is to either use the class directly or subclass it to
    make a more specific implementation (see for example scale.py and
    update.py)

    :param heatclient: An authenticated instance of the Heat client
    :type  heatclient: heatclient.v1.client.Client

    :param stack_id: The name or UUID of the stack
    :type  stack_id: str
    """

    def __init__(self, heatclient, stack_id=None):
        self.heatclient = heatclient
        self.stack_id = stack_id

        self.stack = utils.get_stack(heatclient, stack_id)

    def environment_pre_deploy(self, environment):
        """A pre-deploy hook to allow subclasses to modify the environment file.

        :param environment: The environment dictionary before deploying
        :type  environment: dict

        :return: The environment file dictionary
        :rtype: dict
        """
        return environment

    def deploy(self, template, environment, files, **kwargs):
        """Deploy a parsed template, merged environment and files dict.

        :param template: The root template, parsed from the source format.
        :type  template: dict

        :param environment: A environment dictionary.
        :type  environment: dict

        :param files: A dictionary of files, where the key is the path and the
                      the value is the file contents.
        :type  files: dict

        :param kwargs: Optional arbitrary kwargs that are passed to Heat
                       create/update.
        :type  kwargs: dict

        :return: Returns the created or updated stack from Heat client
        :rtype: dict
        """

        environment = self.environment_pre_deploy(environment)

        stack_args = {
            'stack_name': self.stack_id,
            'template': template,
            'environment': environment,
            'files': files,
            'timeout_mins': 420,
        }

        stack_args.update(kwargs)

        if self.stack is None:
            LOG.info('Creating stack: %s', self.stack_id)
            for k, v in stack_args.items():
                LOG.debug('Stack create param %s: %s', k, v)
            return self.heatclient.stacks.create(**stack_args)
        else:
            LOG.info('Updating stack: %s', self.stack_id)
            # Make sure existing parameters for stack are reused
            stack_args['existing'] = 'true'
            for k, v in stack_args.items():
                LOG.debug('Stack update param %s: %s', k, v)
            return self.heatclient.stacks.update(self.stack.id, **stack_args)


class FileDeployManager(DeployManager):
    """A manager to handle deploying to Heat.

    The intended usage is to either use the class directly or subclass it to
    make a more specific implementation (see for example scale.py and
    update.py)

    :param heatclient: An authenticated instance of the Heat client
    :type  heatclient: heatclient.v1.client.Client

    :param stack_id: The name or UUID of the stack
    :type  stack_id: str
    """

    def deploy(self, template_path, environment_files, parameters=None,
               **kwargs):
        """Deploy to Heat from the local file-system

        :param template_path: The root template
        :type  template_path: dict

        :param environment_files: A list of environment files
        :type  environment_files: dict

        :param kwargs: Optional arbitary kwargs that are passed to Heat
                       create/update.
        :type  kwargs: dict

        :return: Returns the created or updated stack from Heat client
        :rtype: dict
        """
        LOG.debug("Processing environment files")
        env_files, env = (
            template_utils.process_multiple_environments_and_files(
                env_paths=environment_files))

        LOG.debug("Getting template contents")
        tpl_files, template = template_utils.get_template_contents(
            template_file=template_path)

        files = dict(list(tpl_files.items()) + list(env_files.items()))

        return super(FileDeployManager, self).deploy(template, env, files,
                                                     parameters=parameters,
                                                     **kwargs)
