#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.rst",
    "INSTALL.md",
    "DEPLOYMENT.md",
    "Makefile",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.production.yml",
    ".env.production.example",
    ".gitignore",
    ".dockerignore",
    "deployment/caddy/Caddyfile",
    "deployment/caddy/Caddyfile.venv",
    "deployment/systemd/tiks.service",
    "deployment/systemd/tiks-periodic.service",
    "deployment/systemd/tiks-periodic.timer",
    "src/Makefile",
    "src/pretix/static/npm_dir/package.json",
    "src/pretix/static/npm_dir/package-lock.json",
    "src/pretix/static/npm_dir/rollup.config.js",
    "docs/package.json",
    "docs/index.html",
    "src/pretix/static/tiksdocs/index.html",
]

IGNORED_RUNTIME_PATHS = [
    ".venv",
    ".tiks",
    ".env.production",
    "docs/node_modules",
    "e2e_screenshots",
    "data",
]


def main():
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    present_runtime = [path for path in IGNORED_RUNTIME_PATHS if (ROOT / path).exists()]

    if missing:
        print("Missing required repository files:")
        for path in missing:
            print(f"  - {path}")
    else:
        print("Required repository files: OK")

    if present_runtime:
        print("\nRuntime/local files exist locally, but should stay ignored:")
        for path in present_runtime:
            print(f"  - {path}")

    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
