===============================
tripleo-common
===============================

A common library for TripleO workflows.

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/tripleo-common
* Source: http://git.openstack.org/cgit/openstack/tripleo-common
* Bugs: http://bugs.launchpad.net/tripleo-common

Features
--------

* TODO


Running the TripleO API in development
--------------------------------------

Setup
=====

    $ sudo pip install tox
    $ tox -e venv
    $ source .tox/venv/bin/activate
    $ cp etc/tripleo/tripleo.conf.sample tripleo.conf

In a development environment, you'll want to update the 'password'
and 'os_auth_url' values in the keystone section.  If you used
instack-undercloud to install the undercloud, these values should be
set to the environment variable $OS_PASSWORD and ~/undercloud-passwords.conf.

To enable CORS support, 'allowed_origin' needs to be set in the '[cors]'
section. This can be set to '*' to allow all domains.

Run the API server
==================

    $ source .tox/venv/bin/activate
    $ tripleo-api --config-file tripleo.conf
