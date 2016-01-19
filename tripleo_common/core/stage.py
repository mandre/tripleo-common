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

from tripleo_common.core import exception


class Stage(object):

    def __init__(self, stage):
        self.uuid = stage['uuid']
        self.name = stage['name']
        self.description = stage['description']
        self.stage = stage['stage']
        self.validations = stage['validations']

    def run(self, plan_id):
        if any(v.missing_plan_id(plan_id) for v in self.validations.values()):
            raise exception.StageRequiresPlan(id=self.uuid)

        if self.status(plan_id) == 'running':
            raise exception.StageAlreadyRunning(id=self.uuid)

        for validation in self.validations.values():
            validation.run(plan_id)

    def stop(self, plan_id):
        if any(v.missing_plan_id(plan_id) for v in self.validations.values()):
            raise exception.StageRequiresPlan(id=self.uuid)

        for validation in self.validations.values():
            validation.stop(plan_id)

    def status(self, plan_id=None):
        all_statuses = [v.status(plan_id) for v in self.validations.values()]
        if all(status == 'new' for status in all_statuses):
            return 'new'
        elif all(status == 'success' for status in all_statuses):
            return 'success'
        elif any(status == 'requires_plan_id' for status in all_statuses):
            return 'requires_plan_id'
        elif any(status == 'running' for status in all_statuses):
            return 'running'
        elif any(status == 'failed' for status in all_statuses):
            return 'failed'
        elif any(status == 'canceled' for status in all_statuses):
            return 'canceled'
        else:
            # Should never happen
            return 'unknown'
