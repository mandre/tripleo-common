# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from heatclient import exc as heatexc


def get_stack(orchestration_client, stack_name):
    """Get the current deployed stack if it exists.

    If it doesn't exist, None is returned and the caller is responsible for
    checking this.
    """

    try:
        stack = orchestration_client.stacks.get(stack_name)
        return stack
    except heatexc.HTTPNotFound:
        pass
