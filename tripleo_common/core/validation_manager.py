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
import glob
import logging
from os import path
import yaml

from oslo_config import cfg
from tripleo_common.core import exception
from tripleo_common.core import stage as stage_class
from tripleo_common.core import validation as validation_class

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

_VALIDATIONS = {}
_STAGES = {}

DEFAULT_METADATA = {
    'name': 'Unnamed',
    'description': 'No description',
    'stage': 'No stage',
    'require_plan': True,
}


def prepare_database():
    global _VALIDATIONS
    global _STAGES
    all_validations = load_validations().values()
    all_stages = load_stages().values()
    for validation in all_validations:
        _VALIDATIONS[validation['uuid']] = \
            validation_class.Validation(validation)
    for stage in all_stages:
        included_validations = dict()
        for loaded_validation in stage['validations']:
            validation_id = loaded_validation['uuid']
            included_validations[validation_id] = _VALIDATIONS[validation_id]
        stage['validations'] = included_validations
        _STAGES[stage['uuid']] = stage_class.Stage(stage)


def load_validations():
    '''Loads all validations.'''
    paths = glob.glob('{}/validations/*.yaml'
                      .format(CONF.validations_base_dir))
    result = {}
    for index, validation_path in enumerate(sorted(paths)):
        with open(validation_path) as f:
            validation = yaml.safe_load(f.read())
            # TODO(mandre) generating uuid should go in validation class
            # TODO(mandre) switch to generating a proper UUID. We need to
            # figure out how to make sure we always assign the same ID to the
            # same test.  One option: sha of the deserialized yaml file, minus
            # some fields like name or description
            uuid = str(index + 1)
            result[uuid] = {
                'uuid': uuid,
                'playbook': validation_path,
                'name': get_validation_metadata(validation, 'name'),
                'description': get_validation_metadata(validation,
                                                       'description'),
                'require_plan': get_validation_metadata(validation,
                                                        'require_plan'),
                'metadata': get_remaining_metadata(validation)
            }
    return result


def get_validation_metadata(validation, key):
    try:
        return validation[0]['vars']['metadata'][key]
    except KeyError:
        return DEFAULT_METADATA.get(key)
    except TypeError:
        LOG.exception("Failed to get validation metadata.")


def get_remaining_metadata(validation):
    try:
        for (k, v) in validation[0]['vars']['metadata'].items():
            if len(bytes(k)) > 255 or len(bytes(v)) > 255:
                LOG.error("Metadata is too long.")
                raise exception.MetadataTooLongError()

        return {k: v for k, v in validation[0]['vars']['metadata'].items()
                if k not in ['name', 'description', 'require_plan']}
    except KeyError:
        return dict()


def load_stages():
    '''Loads all validation types and includes the related validations.'''
    paths = glob.glob('{}/stages/*.yaml'.format(CONF.validations_base_dir))
    result = {}
    all_validations = load_validations().values()
    for index, stage_path in enumerate(sorted(paths)):
        with open(stage_path) as f:
            stage = yaml.safe_load(f.read())
            stage_uuid = str(index + 1)
            validations = included_validation(stage,
                                              stage_path, all_validations)
            result[stage_uuid] = {
                'uuid': stage_uuid,
                'name': get_validation_metadata(stage, 'name'),
                'description': get_validation_metadata(stage, 'description'),
                'stage': get_validation_metadata(stage, 'stage'),
                'validations': validations,
            }
    return result


def included_validation(stage, stage_path, all_validations):
    '''Returns all validations included in the validation_type.'''
    validations = []
    for entry in stage:
        if 'include' in entry:
            included_playbook_path = entry['include']
            stage_directory = path.dirname(stage_path)
            normalised_path = path.normpath(
                path.join(stage_directory, included_playbook_path))
            matching_validations = [v for v in all_validations
                                    if v['playbook'] == normalised_path]
            if len(matching_validations) > 0:
                validations.append(matching_validations[0])
    return validations


def get_validation(validation_id):
    if validation_id not in _VALIDATIONS:
        raise exception.ValidationDoesNotExistError(id=validation_id)
    return _VALIDATIONS[validation_id]


def get_stage(stage_id):
    if stage_id not in _STAGES:
        raise exception.StageDoesNotExistError(id=stage_id)
    return _STAGES[stage_id]


def get_all_validations():
    return collections.OrderedDict(sorted(_VALIDATIONS.items(),
                                          key=lambda t: t[0])).values()


def get_all_stages():
    return collections.OrderedDict(sorted(_STAGES.items(),
                                          key=lambda t: t[0])).values()
