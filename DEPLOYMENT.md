# GitHub and VPS deployment guide

This guide shows the shortest safe path to upload tiks to GitHub and deploy it on a VPS with Docker Compose, PostgreSQL, Redis, and Caddy HTTPS.

## 1. Prepare the project for GitHub

Do not upload local runtime files, virtual environments, databases, or secrets. The repository is already configured to ignore:

- `.venv/`
- `.tiks/`
- `.env.production`
- `data/`
- `e2e_screenshots/`
- `docs/node_modules/`
- Python caches and test caches

If your local `.git` folder is broken or empty, remove it and initialize Git again:

```bash
rmdir .git
git init
git branch -M main
```

Then connect your GitHub repository:

```bash
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
git add .
git commit -m "Prepare tiks for VPS deployment"
git push -u origin main
```

If you use HTTPS instead of SSH:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
```

## 2. Prepare the VPS

Install Docker and the Docker Compose plugin on the VPS. On Ubuntu:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc >/dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in after adding your user to the `docker` group.

Open these firewall ports:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Point your domain DNS records to the VPS IP before starting Caddy:

```text
A     your-domain.com      VPS_IP
A     www.your-domain.com  VPS_IP
```

## 3. Configure production

Clone the repository on the VPS:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

Create the production env file:

```bash
cp .env.production.example .env.production
nano .env.production
```

Change at least these values:

```text
TIKS_DOMAIN=your-domain.com
TIKS_CADDY_EMAIL=admin@your-domain.com
POSTGRES_PASSWORD=use-a-long-random-password
PRETIX_PRETIX_URL=https://your-domain.com
PRETIX_DATABASE_PASSWORD=use-the-same-long-random-password
PRETIX_MAIL_FROM=tickets@your-domain.com
PRETIX_MAIL_HOST=your-smtp-host
PRETIX_MAIL_PORT=587
PRETIX_MAIL_USER=your-smtp-user
PRETIX_MAIL_PASSWORD=your-smtp-password
PRETIX_MAIL_TLS=true
```

If you want both root and `www`, set:

```text
TIKS_DOMAIN=your-domain.com, www.your-domain.com
```

## 4. Start production

Build and start:

```bash
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml build
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml up -d
```

Watch logs:

```bash
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml logs -f --tail=200
```

Create the first administrator:

```bash
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml run --rm -e AUTOMIGRATE=skip web createsuperuser
```

Open:

```text
https://your-domain.com/control/
```

## 5. Updating after a GitHub push

On the VPS:

```bash
git pull
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml build
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml up -d
```

Migrations run automatically when the web container starts unless `AUTOMIGRATE=skip` is set.

## 6. Backups

Back up these Docker volumes:

- `tiks-production_tiks-db`: PostgreSQL data
- `tiks-production_tiks-data`: uploaded media and app data
- `tiks-production_caddy-data`: TLS certificates

Example database backup:

```bash
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml exec db pg_dump -U tiks tiks > tiks-backup.sql
```

## 7. Quick health checks

```bash
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml ps
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml logs web --tail=100
TIKS_ENV_FILE=.env.production docker compose -f docker-compose.production.yml logs proxy --tail=100
```

The deployment is healthy when `web`, `db`, `redis`, and `proxy` are running, Caddy has issued a certificate, and `/control/` loads over HTTPS.
