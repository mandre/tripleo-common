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

import datetime
import uuid

from tripleo_common.api import database
from tripleo_common.core import exception


def get_results(result_ids):
    if len(result_ids) == 0:
        return []

    sql = "select * from validation_results where uuid in ({}) order by date" \
        .format(','.join(['?'] * len(result_ids)))
    results = database.query_db(sql, result_ids)
    if not results:
        raise exception.ValidationResultDoesNotExistError(id=result_ids)

    return [ValidationResult(r) for r in results]


def get_all_results(plan_id=None):
    sql = "select * from validation_results"
    args = []
    if plan_id:
        sql = sql + " where plan_id = ?"
        args = [plan_id]
    sql = sql + " order by date"
    results = database.query_db(sql, args)
    return [ValidationResult(r) for r in results]


class ValidationResult(object):

    def __init__(self, result={}):
        self.uuid = result.get('uuid') or str(uuid.uuid4())
        self.date = result.get('date') or \
            datetime.datetime.utcnow().isoformat() + 'Z'
        self.status = result.get('status') or 'new'
        self.validation = result.get('validation')
        self.detailed_description = result.get('detailed_description')
        self.plan_id = result.get('plan_id')
        self.arguments = result.get('arguments')

    def insert(self):
        sql = """insert into validation_results
                (uuid, date, validation, status, plan_id) values (?,?,?,?,?)"""
        database.get_db().execute(
            sql,
            [self.uuid, self.date, self.validation, self.status, self.plan_id])
        database.get_db().commit()

    def update(self, **kwarg):
        args = dict((k, v) for k, v in kwarg.iteritems() if v)
        sql = "update validation_results set {} where uuid=?".format(
            ','.join(["{}=?".format(k) for k in args]))

        database.get_db().execute(sql, args.values() + [self.uuid])
        database.get_db().commit()
