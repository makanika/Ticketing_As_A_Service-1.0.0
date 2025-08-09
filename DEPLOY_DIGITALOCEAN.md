# Deploying DjangoSiteBuilder to DigitalOcean (Production)

This guide walks you through deploying this Django app on a DigitalOcean Droplet with Gunicorn + Nginx + systemd, using Ubuntu 22.04/24.04. It also covers static files, HTTPS, and django-allauth callbacks.

If you prefer App Platform or Kubernetes, see the Notes at the end.

---

## 1) Create a Droplet
- Image: Ubuntu 22.04 LTS or 24.04 LTS
- Plan: Basic (choose based on expected traffic; 1–2GB RAM is fine to start)
- Datacenter region: choose near your users
- Authentication: SSH keys (recommended)
- Enable backups (optional)

Point a domain (e.g., example.com) to the Droplet’s public IP via an A record.

---

## 2) Connect and prepare the server
SSH into the droplet as root or a sudo user.

```bash
ssh root@your_server_ip
# or
ssh youruser@your_server_ip
```

Install dependencies and secure firewall:

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install python3 python3-venv python3-pip git nginx ufw
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

Optionally create a deploy user:

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG sudo deploy
sudo -u deploy -H bash
```

---

## 3) Clone the repo and set up Python
Choose a directory (e.g., /srv/Ticketing_As_A_Service-1.0.0):

```bash
sudo mkdir -p /srv/Ticketing_As_A_Service-1.0.0
sudo chown "$USER":"$USER" /srv/Ticketing_As_A_Service-1.0.0
cd /srv/Ticketing_As_A_Service-1.0.0

git clone <YOUR_GIT_REPO_URL> .
# Or if already cloned, pull latest
# git pull origin main

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Gunicorn is not in requirements.txt; install it explicitly
pip install gunicorn
```

---

## 4) Configure Django (Production)
Edit core/settings.py for production:
- DEBUG = False
- ALLOWED_HOSTS = ["yourdomain.com", "www.yourdomain.com"]
- Ensure STATIC_ROOT is set (already set to `BASE_DIR / 'staticfiles'`)
- Consider reading SECRET_KEY and DB config from environment variables (recommended)

Collect static files and run migrations:

```bash
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser  # if needed
```

---

## 5) Create a systemd service for Gunicorn
Create /etc/systemd/system/ticketing.service:

```ini
[Unit]
Description=Gunicorn for Ticketing_As_A_Service-1.0.0
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/Ticketing_As_A_Service-1.0.0
Environment="DJANGO_SETTINGS_MODULE=core.settings"
ExecStart=/srv/Ticketing_As_A_Service-1.0.0/venv/bin/gunicorn \
  --workers 3 \
  --bind unix:/run/ticketing.sock \
  core.wsgi:application
RuntimeDirectory=ticketing
RuntimeDirectoryMode=0755
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Create runtime dir and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ticketing
sudo systemctl start ticketing
sudo systemctl status ticketing
```

You should see the socket /run/ticketing.sock created.

---

## 6) Configure Nginx
Create /etc/nginx/sites-available/ticketing:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    client_max_body_size 25M;

    location = /favicon.ico { access_log off; log_not_found off; }

    # Static files
    location /static/ {
        alias /srv/Ticketing_As_A_Service-1.0.0/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    # Proxy to Gunicorn via Unix socket
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/ticketing.sock;
    }
}
```

Enable the config:

```bash
sudo ln -s /etc/nginx/sites-available/ticketing /etc/nginx/sites-enabled/ticketing
sudo nginx -t
sudo systemctl reload nginx
```

---

## 7) HTTPS with Let’s Encrypt
Install certbot and issue a certificate (requires DNS pointing to server):

```bash
sudo apt -y install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com --redirect --agree-tos -m you@example.com
```

Auto-renewal is installed by default via systemd timer.

---

## 8) django-allauth callbacks and Sites
Update Allauth SocialApp entries in Django admin:
- http://yourdomain.com/admin
- Social applications > Add
- Create one for Google, one for Microsoft
- Add your Site (SITE_ID=1); update Sites to `yourdomain.com`

Redirect URLs required at the provider:
- Google:     `https://yourdomain.com/accounts/google/login/callback/`
- Microsoft:  `https://yourdomain.com/accounts/microsoft/login/callback/`

---

## 9) Ongoing operations
- Update code:
  ```bash
  cd /srv/Ticketing_As_A_Service-1.0.0
  git pull origin main
  source venv/bin/activate
  pip install -r requirements.txt
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  sudo systemctl restart ticketing
  ```
- Logs:
  ```bash
  journalctl -u ticketing -f --no-pager
  sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
  ```

---

## Database (Optional: Managed PostgreSQL)
SQLite can work for light traffic but is not recommended for production.

Suggested approach:
- Provision DigitalOcean Managed PostgreSQL
- Add `psycopg2-binary` and `dj-database-url` to requirements
- Update settings.py to read DATABASE_URL env var (e.g., `postgres://...`)

Example snippet in settings.py:
```python
import os
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
}
```

Set `DATABASE_URL` in the systemd service via `Environment=` or export it in an env file loaded by the service.

---

## App Platform / Docker (Alternative)
- Build a Docker image with Gunicorn
- Push to a registry (Docker Hub or DOCR)
- Use DigitalOcean App Platform, configure environment variables, static files, and run command: `gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 3`

---

## Security checklist
- DEBUG = False
- Strong SECRET_KEY (read from environment)
- Limited ALLOWED_HOSTS
- HTTPS only; redirect HTTP → HTTPS (certbot `--redirect` does this)
- Regular OS and dependency updates
- Restrict SSH and keep firewall enabled
