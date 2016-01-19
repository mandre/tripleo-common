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

import collections
import itertools
import json
import threading

from tripleo_common.api import utils
from tripleo_common.core import exception
from tripleo_common.core import validation_result
from tripleo_common.utils import ansible_runner


class Validation(object):

    def __init__(self, validation):
        self.uuid = validation['uuid']
        self.name = validation['name']
        self.playbook = validation['playbook']
        self.description = validation['description']
        self.require_plan = validation['require_plan']
        self.ref = validation['metadata'].pop('ref', None)
        self.metadata = validation['metadata']
        self._threads = dict()
        self._results = collections.defaultdict(list)

    def missing_plan_id(self, plan_id):
        return self.require_plan and not plan_id

    def _plan_name(self, plan_id):
        if self.missing_plan_id(plan_id):
            raise exception.ValidationRequiresPlan(id=self.uuid)

        return plan_id if self.require_plan else 'default_plan'

    def result_ids(self, plan_id=None):
        if plan_id:
            return self._results[self._plan_name(plan_id)]
        else:
            return list(itertools.chain(*self._results.values()))

    def results(self, plan_id=None):
        result_ids = self.result_ids(plan_id)
        return validation_result.get_results(result_ids)

    def status(self, plan_id=None):
        if self.missing_plan_id(plan_id):
            return 'requires_plan_id'

        result_ids = self.result_ids(plan_id)
        if len(result_ids) > 0:
            return validation_result.get_results([result_ids[-1]])[-1].status \
                or 'new'
        else:
            return 'new'

    @utils.with_app_context
    def thread_run_validation(self, cancel_event, plan_id):
        result = validation_result.ValidationResult()
        result.validation = self.uuid
        result.plan_id = plan_id
        result.status = 'running'

        result.insert()
        self._results[self._plan_name(plan_id)].append(result.uuid)

        run_result = ansible_runner.run(self.playbook, cancel_event)
        success = all((r.get('success') for r in run_result.values()))
        status = 'success' if success else 'failed'

        result.update(status=status,
                      detailed_description=json.dumps(run_result))

    def run(self, plan_id):
        previous_thread = self._threads.get(self._plan_name(plan_id))
        if previous_thread and previous_thread.is_alive():
            raise exception.ValidationAlreadyRunning(id=self.uuid)

        cancel_event = threading.Event()
        thread = threading.Thread(
            target=self.thread_run_validation,
            args=(cancel_event, plan_id))
        thread.cancel_event = cancel_event
        self._threads[self._plan_name(plan_id)] = thread
        thread.start()

    def stop(self, plan_id):
        thread = self._threads.get(self._plan_name(plan_id))
        if not (thread and thread.is_alive()):
            raise exception.ValidationNotRunning(id=self.uuid)

        result_id = self.result_ids(plan_id)[-1]
        result = validation_result.get_results([result_id])[-1]
        result.update(status='canceled')

        thread.cancel_event.set()
        self._threads[self._plan_name(plan_id)] = None
