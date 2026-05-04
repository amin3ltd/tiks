#!/usr/bin/env python3
import argparse
import getpass
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TIKS_DIR = ROOT / ".tiks"
VENV_DIR = ROOT / ".venv"


def ask(prompt, default=None):
    suffix = f" [{default}]" if default not in (None, "") else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def ask_bool(prompt, default=True):
    default_text = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_text}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def choose(prompt, choices, default):
    rendered = "/".join(f"[{c}]" if c == default else c for c in choices)
    while True:
        value = input(f"{prompt} ({rendered}): ").strip().lower() or default
        if value in choices:
            return value
        print(f"Choose one of: {', '.join(choices)}")


def run(cmd, *, env=None, cwd=ROOT, check=True, input_text=None):
    printable = " ".join(str(c) for c in cmd)
    print(f"\n$ {printable}")
    return subprocess.run(
        [str(c) for c in cmd],
        cwd=cwd,
        env=env,
        check=check,
        text=True,
        input=input_text,
    )


def capture(cmd, *, env=None, cwd=ROOT, check=True):
    return subprocess.run(
        [str(c) for c in cmd],
        cwd=cwd,
        env=env,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def find_python311():
    requested = os.environ.get("TIKS_PYTHON")
    candidates = [requested] if requested else []
    candidates += ["python3.11", "python3"]
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        path = shutil.which(candidate)
        if not path:
            continue
        result = capture(
            [path, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip() == "3.11":
            return Path(path)
    return None


def ensure_venv():
    python = find_python311()
    if not python:
        print(
            textwrap.dedent(
                """
                Python 3.11 was not found.

                This project should not be installed into Python 3.13 directly.
                Install Python 3.11 first, then rerun this installer. Examples:

                  pyenv install 3.11.9
                  pyenv local 3.11.9

                Or set TIKS_PYTHON=/path/to/python3.11 before running make install.
                """
            ).strip()
        )
        sys.exit(1)

    if not VENV_DIR.exists():
        run([python, "-m", "venv", VENV_DIR])
    else:
        print(f"Using existing virtual environment: {VENV_DIR}")

    venv_python = VENV_DIR / "bin" / "python"
    run([venv_python, "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"])
    return venv_python


def install_python_packages(venv_python, mode):
    if mode == "production":
        run([venv_python, "-m", "pip", "install", "-e", ".[memcached]", "gunicorn"])
    else:
        run([venv_python, "-m", "pip", "install", "-e", ".[dev]"])


def psql_env(password):
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    return env


def psql_value(admin, host, port, sql, password):
    result = capture(
        [
            "psql",
            "-h",
            host,
            "-p",
            port,
            "-U",
            admin,
            "-d",
            "postgres",
            "-tAc",
            sql,
        ],
        env=psql_env(password),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "psql command failed")
    return result.stdout.strip()


def psql_exec(admin, host, port, sql, password):
    result = run(
        ["psql", "-h", host, "-p", port, "-U", admin, "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", sql],
        env=psql_env(password),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("psql command failed")


def qident(value):
    return '"' + value.replace('"', '""') + '"'


def qlit(value):
    return "'" + value.replace("'", "''") + "'"


def configure_postgres(mode):
    if not shutil.which("psql"):
        print("PostgreSQL client 'psql' was not found. Install it or choose SQLite.")
        sys.exit(1)

    print("\nPostgreSQL setup")
    host = ask("Database host", "localhost")
    port = ask("Database port", "5432")
    dbname = ask("Database name", "tiks")
    app_user = ask("Application database user", "tiks")
    app_password = getpass.getpass("Application database password: ")

    create = ask_bool("Should the installer create/update the PostgreSQL database now?", True)
    if create:
        admin = ask("PostgreSQL admin user", "postgres")
        admin_password = getpass.getpass("PostgreSQL admin password (leave empty for peer/trust auth): ")

        try:
            db_exists = psql_value(admin, host, port, f"SELECT 1 FROM pg_database WHERE datname = {qlit(dbname)}", admin_password)
            role_exists = psql_value(admin, host, port, f"SELECT 1 FROM pg_roles WHERE rolname = {qlit(app_user)}", admin_password)
        except RuntimeError as e:
            print(f"Could not connect as PostgreSQL admin: {e}")
            sys.exit(1)

        if role_exists:
            if ask_bool(f"Role '{app_user}' exists. Update its password?", False):
                psql_exec(admin, host, port, f"ALTER ROLE {qident(app_user)} WITH LOGIN PASSWORD {qlit(app_password)}", admin_password)
        else:
            psql_exec(admin, host, port, f"CREATE ROLE {qident(app_user)} WITH LOGIN PASSWORD {qlit(app_password)}", admin_password)

        if db_exists:
            action = choose(
                f"Database '{dbname}' already exists. Use/update it or replace it?",
                ["update", "replace", "abort"],
                "update",
            )
            if action == "abort":
                sys.exit(1)
            if action == "replace":
                confirm = ask(f"Type the database name to confirm replacing '{dbname}'")
                if confirm != dbname:
                    print("Confirmation did not match. Aborting.")
                    sys.exit(1)
                psql_exec(
                    admin,
                    host,
                    port,
                    f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = {qlit(dbname)}",
                    admin_password,
                )
                psql_exec(admin, host, port, f"DROP DATABASE {qident(dbname)}", admin_password)
                psql_exec(admin, host, port, f"CREATE DATABASE {qident(dbname)} OWNER {qident(app_user)}", admin_password)
            else:
                psql_exec(admin, host, port, f"ALTER DATABASE {qident(dbname)} OWNER TO {qident(app_user)}", admin_password)
        else:
            psql_exec(admin, host, port, f"CREATE DATABASE {qident(dbname)} OWNER {qident(app_user)}", admin_password)

    return {
        "backend": "postgresql",
        "name": dbname,
        "user": app_user,
        "password": app_password,
        "host": host,
        "port": port,
    }


def sqlite_database(mode):
    data_dir = TIKS_DIR / f"{mode}-data"
    return {
        "backend": "sqlite3",
        "name": str(data_dir / "db.sqlite3"),
        "user": "",
        "password": "",
        "host": "",
        "port": "",
    }


def configure_database(mode, quick=False):
    if quick:
        print("Using SQLite for the local quick install.")
        return sqlite_database(mode)

    default = "sqlite"
    backend = choose("Database backend", ["sqlite", "postgres"], default)
    if backend == "sqlite":
        return sqlite_database(mode)
    return configure_postgres(mode)


def write_config(mode, db, quick=False):
    TIKS_DIR.mkdir(exist_ok=True)
    data_dir = TIKS_DIR / f"{mode}-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path = TIKS_DIR / f"{mode}.cfg"
    default_url = "http://localhost:8000" if mode == "local" else "https://tiks.cc"
    url = default_url if quick else ask("Site URL", default_url)
    registration = "true" if mode == "local" else "false"
    if mode == "production":
        print("\nMail setup")
        mail_from = ask("Sender email", "tickets@tiks.cc")
        mail_host = ask("SMTP host", "localhost")
        mail_port = ask("SMTP port", "25")
        mail_user = ask("SMTP username (leave empty if not needed)", "")
        mail_password = getpass.getpass("SMTP password (leave empty if not needed): ")
        mail_tls = "true" if ask_bool("Use SMTP STARTTLS?", mail_port == "587") else "false"
        debug = "false"
    else:
        mail_from = "tiks@localhost"
        mail_host = "localhost"
        mail_port = "25"
        mail_user = ""
        mail_password = ""
        mail_tls = "false"
        debug = "true"
    proxy_settings = ""
    if mode == "production":
        proxy_settings = """trust_x_forwarded_proto=true
trust_x_forwarded_for=true
trust_x_forwarded_host=true
"""

    config = f"""[pretix]
instance_name=tiks
url={url}
datadir={data_dir}
registration={registration}
{proxy_settings}plugins_default=pretix.plugins.sendmail,pretix.plugins.statistics,pretix.plugins.checkinlists
currency=ETB

[locale]
default=en
timezone=Africa/Addis_Ababa

[database]
backend={db['backend']}
name={db['name']}
user={db['user']}
password={db['password']}
host={db['host']}
port={db['port']}

[mail]
from={mail_from}
host={mail_host}
port={mail_port}
user={mail_user}
password={mail_password}
tls={mail_tls}

[django]
debug={debug}
"""
    config_path.write_text(config, encoding="utf-8")
    env_path = TIKS_DIR / f"{mode}.env"
    env_path.write_text(
        f"export PRETIX_CONFIG_FILE='{config_path}'\nexport PATH='{VENV_DIR / 'bin'}':$PATH\n",
        encoding="utf-8",
    )
    return config_path


def app_env(config_path):
    env = os.environ.copy()
    env["PRETIX_CONFIG_FILE"] = str(config_path)
    env["DJANGO_SETTINGS_MODULE"] = "pretix.settings"
    return env


def run_migrations(venv_python, config_path):
    run([venv_python, "-m", "pretix", "migrate", "--noinput"], env=app_env(config_path))


def prepare_assets(venv_python, config_path, mode):
    if mode == "local":
        return
    if not shutil.which("npm"):
        print("Skipping production asset build because npm was not found.")
        return
    if ask_bool("Build production static assets now?", True):
        run([venv_python, "-m", "pretix", "rebuild"], env=app_env(config_path))


def maybe_create_superuser(venv_python, config_path):
    if ask_bool("Create an admin user now?", True):
        run([venv_python, "-m", "pretix", "createsuperuser"], env=app_env(config_path))


def main():
    parser = argparse.ArgumentParser(description="Install and prepare tiks")
    parser.add_argument("--mode", choices=["local", "production"], default="local")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use local defaults without prompts: SQLite, localhost URL, and no admin-user prompt",
    )
    parser.add_argument("--skip-deps", action="store_true", help="Do not install Python packages")
    parser.add_argument("--skip-superuser", action="store_true", help="Do not prompt for admin user creation")
    args = parser.parse_args()

    if args.quick and args.mode != "local":
        parser.error("--quick is only supported for local installs")

    print(f"Preparing tiks in {args.mode} mode")
    venv_python = ensure_venv()
    if not args.skip_deps:
        install_python_packages(venv_python, args.mode)
    db = configure_database(args.mode, quick=args.quick)
    config_path = write_config(args.mode, db, quick=args.quick)
    run_migrations(venv_python, config_path)
    prepare_assets(venv_python, config_path, args.mode)
    if args.quick:
        print("Skipping admin-user prompt for quick install. Create one later with: make createsuperuser-local")
    elif not args.skip_superuser:
        maybe_create_superuser(venv_python, config_path)

    if args.mode == "local":
        print("\nDone. Start local development with:")
        print("  make run-local")
        print("Then open http://localhost:8000/control/")
    else:
        print("\nDone. Start production with:")
        print("  make run-production")
        print("Put a reverse proxy with HTTPS in front of 127.0.0.1:8000 for tiks.cc.")


if __name__ == "__main__":
    main()
