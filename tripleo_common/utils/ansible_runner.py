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

# Import explicitly in this order to fix the import issues:
# https://bugzilla.redhat.com/show_bug.cgi?id=1065251
import ansible.playbook
import ansible.constants as C  # flake8: noqa
import ansible.utils.template
from ansible import callbacks  # flake8: noqa


class ValidationCancelled(Exception):
    pass


class SilentPlaybookCallbacks(object):
    '''Unlike callbacks.PlaybookCallbacks this doesn't print to stdout.'''

    def __init__(self, cancel_event):
        self.cancel_event = cancel_event

    def on_start(self):
        callbacks.call_callback_module('playbook_on_start')

    def on_notify(self, host, handler):
        callbacks.call_callback_module('playbook_on_notify', host, handler)

    def on_no_hosts_matched(self):
        callbacks.call_callback_module('playbook_on_no_hosts_matched')

    def on_no_hosts_remaining(self):
        callbacks.call_callback_module('playbook_on_no_hosts_remaining')

    def on_task_start(self, name, is_conditional):
        callbacks.call_callback_module('playbook_on_task_start', name,
                                       is_conditional)
        if self.cancel_event and self.cancel_event.is_set():
            raise ValidationCancelled()

    def on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None,
                       confirm=False, salt_size=None, salt=None, default=None):
        callbacks.call_callback_module(
            'playbook_on_vars_prompt',
            varname,
            private=private,
            prompt=prompt,
            encrypt=encrypt,
            confirm=confirm,
            salt_size=salt_size,
            salt=None,
            default=default)

    def on_setup(self):
        callbacks.call_callback_module('playbook_on_setup')

    def on_import_for_host(self, host, imported_file):
        callbacks.call_callback_module('playbook_on_import_for_host', host,
                                       imported_file)

    def on_not_import_for_host(self, host, missing_file):
        callbacks.call_callback_module('playbook_on_not_import_for_host', host,
                                       missing_file)

    def on_play_start(self, name):
        callbacks.call_callback_module('playbook_on_play_start', name)

    def on_stats(self, stats):
        callbacks.call_callback_module('playbook_on_stats', stats)


def run(playbook, cancel_event):
    C.HOST_KEY_CHECKING = False
    stats = callbacks.AggregateStats()
    playbook_callbacks = SilentPlaybookCallbacks(cancel_event)
    runner_callbacks = callbacks.DefaultRunnerCallbacks()
    playbook = ansible.playbook.PlayBook(
        playbook=playbook,
        # TODO we should use a dynamic inventory based on data coming from
        # tripleo-common/heat/ironic
        # http://docs.ansible.com/ansible/developing_api.html
        host_list='hosts',
        stats=stats,
        callbacks=playbook_callbacks,
        runner_callbacks=runner_callbacks)
    try:
        result = playbook.run()
    except ValidationCancelled:
        result = {}
        for host in playbook.inventory.list_hosts():
            result[host] = {
                'failures': 1,
                'unreachable': 0,
                'description': "Validation was cancelled.",
            }

    for host, status in result.items():
        success = status['failures'] == 0 and status['unreachable'] == 0
        result[host]['success'] = success
    return result
