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

from contextlib import closing
import flask
import sqlite3

from oslo_config import cfg

CONF = cfg.CONF


def connect_to_database():
    def make_dicts(cursor, row):
        return dict((cursor.description[idx][0], value)
                    for idx, value in enumerate(row))

    rv = sqlite3.connect(CONF.validations_database)
    rv.row_factory = make_dicts
    return rv


def init_db():
    with closing(connect_to_database()) as db:
        app = flask.Flask(__name__)
        with app.open_resource('../../schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    db = getattr(flask.g, '_database', None)
    if db is None:
        db = flask.g._database = connect_to_database()
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv
