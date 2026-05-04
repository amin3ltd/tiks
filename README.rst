tiks
====

Reinventing ticket presales, one ticket at a time.

Quick Install
-------------

The quickest local setup uses SQLite and sensible defaults, creates a Python 3.11 virtual environment, installs the
app, writes config, and runs migrations. If Python 3.11 is not installed, ``make install`` automatically falls back to
Docker so a machine with only Python 3.13 can still run tiks locally.

.. code-block:: bash

   ./install.sh

Or, if you prefer Make directly:

.. code-block:: bash

   make doctor
   make install
   make run-local

Then open http://localhost:8000/control/. Create the first admin account with:

.. code-block:: bash

   make createsuperuser-local

For PostgreSQL, a custom site URL, or the older guided setup, run ``make install-custom``. If the database already
exists, the custom installer asks whether to update it, replace it, or abort.

Deploying tiks.cc
-----------------

On the server, use the production installer:

.. code-block:: bash

   make install-production
   make run-production

This prepares the venv, database, migrations, SMTP settings, and production config. ``make run-production`` binds
Gunicorn to ``127.0.0.1:8000``; put HTTPS in front of it for ``tiks.cc``.

Docker Alternative
------------------

Docker is still available:

.. code-block:: bash

   make docker-install
   make docker-start

See ``INSTALL.md`` for all commands and production Docker/Caddy instructions.
For GitHub upload and VPS deployment, see ``DEPLOYMENT.md``.

Project status & release cycle
------------------------------

While there is always a lot to do and improve on, tiks is built on a stable ticketing platform used for thousands of
events and conferences that sold millions of tickets combined.

The codebase is derived from pretix and keeps its internal Python module names for compatibility. User-facing
branding has been changed to tiks.

Support
-------

This project is free and open source software. For local setup and operations, start with ``INSTALL.md``.

Contributing
------------
If you want to contribute to tiks, please read the `developer documentation`_
in our documentation. If you have any further questions, please do not hesitate to ask!

Code of Conduct
---------------
We have a `Code of Conduct`_ in place that applies to all project contributions,
including issues, pull requests, etc.

License
-------

The code in this repository is covered by different licenses. Most of it is available to everyone under the terms of
the GNU AGPL license v3 with additional terms. See the LICENSE file for the complete license details.

.. _developer documentation: https://docs.pretix.eu/dev/development/index.html
.. _Code of Conduct: https://docs.pretix.eu/dev/development/contribution/codeofconduct.html
