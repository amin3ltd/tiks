# Installing tiks

The quickest installer creates a Python 3.11 virtual environment, writes local SQLite configuration, installs dependencies, and runs migrations without asking setup questions.

Your host currently has Python 3.13.3, but this project should run on Python 3.11. Install Python 3.11 once, then the installer handles the venv automatically.

## Fastest Local Install

Run:

```bash
./install.sh
make run-local
```

Open:

```text
http://localhost:8000/control/
```

Create the first admin user:

```bash
make createsuperuser-local
```

## Local Development

Run:

```bash
make doctor
make install
```

If Python 3.11 is installed, `make install` uses the quick virtualenv installer with SQLite defaults. If only Python 3.13 is available, it automatically falls back to Docker so you can still test locally.

To use the guided installer for PostgreSQL, a custom site URL, or admin-user creation during setup:

```bash
make install-custom
```

To force the older virtualenv command name:

```bash
make install-venv
```

The quick virtualenv installer will:

- find Python 3.11
- create `.venv`
- install Python dependencies
- use SQLite
- create `.tiks/local.cfg`
- run database migrations

The custom installer also asks for a database backend, optional PostgreSQL settings, a site URL, and whether to create an admin user.

Start the local server:

```bash
make run-local
```

Open:

```text
http://localhost:8000/control/
```

If `make install` fell back to Docker, start and open:

```bash
make docker-start
```

```text
http://localhost:8080/control/
```

## Local PostgreSQL

When the installer asks for a database backend, choose `postgres`.

It will ask for:

- database host and port
- database name
- application database username
- application database password
- PostgreSQL admin username and password if you want it to create the DB

If the database already exists, the installer asks whether to:

- `update`: keep it and run migrations
- `replace`: drop and recreate it
- `abort`: stop without changing it

If you choose SQLite, no PostgreSQL setup is needed.

## Production Venv Install

On the server for `tiks.cc`, run:

```bash
make install-production
```

The production installer will:

- create or reuse `.venv`
- install production Python dependencies
- use SQLite by default if you do not provide a database
- ask for PostgreSQL credentials and admin access when you choose PostgreSQL
- create/update/replace the database as requested
- write `.tiks/production.cfg`
- ask for SMTP settings
- run migrations
- optionally build production assets
- ask whether to create an admin user

Start the production app process:

```bash
make run-production
```

This binds Gunicorn to `127.0.0.1:8000`. Put HTTPS in front of it with Caddy, Nginx, or another reverse proxy for `tiks.cc`.

## Docker Alternative

Docker remains available if you prefer containers or do not want to install Python 3.11 on the host:

```bash
make docker-install
make docker-start
make docker-createsuperuser
```

Open:

```text
http://localhost:8080/control/
```

For Docker production with automatic HTTPS through Caddy:

```bash
make prod-init
```

Edit `.env.production`, then:

```bash
make prod-build
make prod-start
make prod-createsuperuser
```

Point DNS for `tiks.cc` and `www.tiks.cc` to your server before starting Caddy.

For a full GitHub-to-VPS checklist, including Docker installation, production environment variables, startup, updates, and backups, see `DEPLOYMENT.md`.

## Useful Commands

```bash
make install
make install-custom
make migrate-local
make shell-local
make createsuperuser-local
make migrate-production
make docker-logs
make prod-logs
```

## Files Created by the Installer

- `.venv/`: Python 3.11 virtual environment
- `.tiks/local.cfg`: local app configuration
- `.tiks/production.cfg`: production app configuration
- `.tiks/local-data/`: local data directory
- `.tiks/production-data/`: production data directory

Internal Python modules and some compatibility identifiers are still named `pretix`; that is intentional so the inherited codebase and plugins keep working.
