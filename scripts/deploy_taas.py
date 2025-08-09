#!/usr/bin/env python3
"""
Automated deployment script for Ticketing_As_A_Service-1.0.0

This script performs a simple, repeatable deployment on a single server for this Django app.
It assumes:
- Ubuntu 22.04/24.04 server with sudo privileges
- You can SSH into the server
- You want to deploy to /srv/Ticketing_As_A_Service-1.0.0

It will:
1) SSH into the server
2) Clone/pull your Git repo to the target directory
3) Create/Update a Python venv and install requirements
4) Run migrate + collectstatic
5) Install/enable a systemd service for Gunicorn
6) Create/enable an Nginx site and reload Nginx

Usage:
  python scripts/deploy_taas.py \
    --host 1.2.3.4 \
    --user deploy \
    --repo git@github.com:you/yourrepo.git \
    --domain yourdomain.com \
    [--branch main] [--port 22]

You may need to enter SSH password or have SSH keys configured.

Note: This is a convenience wrapper using subprocess + ssh/scp. For idempotent, multi-host deployments,
consider Ansible or Terraform.
"""

import argparse
import os
import subprocess
import textwrap

SERVICE_NAME = "ticketing"
APP_DIR = "/srv/Ticketing_As_A_Service-1.0.0"
PYTHON_BIN = f"{APP_DIR}/venv/bin/python"
PIP_BIN = f"{APP_DIR}/venv/bin/pip"
GUNICORN_BIN = f"{APP_DIR}/venv/bin/gunicorn"
SYSTEMD_PATH = f"/etc/systemd/system/{SERVICE_NAME}.service"
NGINX_SITE_PATH = "/etc/nginx/sites-available/ticketing"
NGINX_SITE_LINK = "/etc/nginx/sites-enabled/ticketing"
SOCKET_PATH = "/run/ticketing.sock"

SYSTEMD_UNIT = f"""
[Unit]
Description=Gunicorn for Ticketing_As_A_Service-1.0.0
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory={APP_DIR}
Environment="DJANGO_SETTINGS_MODULE=core.settings"
ExecStart={GUNICORN_BIN} --workers 3 --bind unix:{SOCKET_PATH} core.wsgi:application
RuntimeDirectory=ticketing
RuntimeDirectoryMode=0755
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""

NGINX_CONF_TEMPLATE = """
server {{
    listen 80;
    server_name {domain} www.{domain};

    client_max_body_size 25M;

    location = /favicon.ico {{ access_log off; log_not_found off; }}

    location /static/ {{
        alias {app_dir}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }}

    location / {{
        include proxy_params;
        proxy_pass http://unix:{socket};
    }}
}}
"""


def run_local(cmd: str):
    print(f"[local] $ {cmd}")
    subprocess.check_call(cmd, shell=True)


def run_remote(host: str, user: str, cmd: str, port: int = 22):
    ssh_cmd = f"ssh -p {port} {user}@{host} '{cmd}'"
    print(f"[remote] $ {ssh_cmd}")
    subprocess.check_call(ssh_cmd, shell=True)


def put_remote_file(host: str, user: str, content: str, remote_path: str, sudo: bool = False, port: int = 22):
    """Copy content to a temp file and scp it to remote path, optionally using sudo mv to final path."""
    import tempfile

    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        tf.write(content)
        local_tmp = tf.name

    try:
        remote_tmp = f"/tmp/{os.path.basename(remote_path)}"
        run_local(f"scp -P {port} {local_tmp} {user}@{host}:{remote_tmp}")
        if sudo:
            run_remote(host, user, f"sudo mv {remote_tmp} {remote_path}")
        else:
            run_remote(host, user, f"mv {remote_tmp} {remote_path}")
    finally:
        os.unlink(local_tmp)


def main():
    parser = argparse.ArgumentParser(description="Deploy Ticketing_As_A_Service-1.0.0")
    parser.add_argument("--host", required=True, help="Server IP or hostname")
    parser.add_argument("--user", required=True, help="SSH user")
    parser.add_argument("--repo", required=True, help="Git repo URL")
    parser.add_argument("--domain", required=True, help="Public domain (e.g. example.com)")
    parser.add_argument("--branch", default="main", help="Git branch to deploy")
    parser.add_argument("--port", type=int, default=22, help="SSH port")

    args = parser.parse_args()

    # Ensure system packages
    run_remote(args.host, args.user, "sudo apt update && sudo apt -y install python3 python3-venv python3-pip git nginx", port=args.port)

    # Create app dir
    run_remote(args.host, args.user, f"sudo mkdir -p {APP_DIR} && sudo chown {args.user}:{args.user} {APP_DIR}", port=args.port)

    # Clone or pull
    run_remote(args.host, args.user, f"test -d {APP_DIR}/.git && (cd {APP_DIR} && git fetch && git checkout {args.branch} && git pull origin {args.branch}) || git clone -b {args.branch} {args.repo} {APP_DIR}", port=args.port)

    # Python env
    run_remote(args.host, args.user, f"cd {APP_DIR} && python3 -m venv venv && . venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn", port=args.port)

    # Django collectstatic + migrate
    run_remote(args.host, args.user, f"cd {APP_DIR} && . venv/bin/activate && {PYTHON_BIN} manage.py migrate --noinput && {PYTHON_BIN} manage.py collectstatic --noinput", port=args.port)

    # systemd unit
    put_remote_file(args.host, args.user, SYSTEMD_UNIT, SYSTEMD_PATH, sudo=True, port=args.port)
    run_remote(args.host, args.user, "sudo systemctl daemon-reload && sudo systemctl enable {svc} && sudo systemctl restart {svc}".format(svc=SERVICE_NAME), port=args.port)

    # nginx site
    nginx_conf = NGINX_CONF_TEMPLATE.format(domain=args.domain, app_dir=APP_DIR, socket=SOCKET_PATH)
    put_remote_file(args.host, args.user, nginx_conf, NGINX_SITE_PATH, sudo=True, port=args.port)
    run_remote(args.host, args.user, f"sudo ln -sf {NGINX_SITE_PATH} {NGINX_SITE_LINK} && sudo nginx -t && sudo systemctl reload nginx", port=args.port)

    print("\nDeployment complete. Verify:")
    print(f"  - http://{args.domain}/  (and configure HTTPS via certbot)")
    print(f"  - systemd: sudo systemctl status {SERVICE_NAME}")
    print("  - logs: journalctl -u ticketing -f --no-pager")


if __name__ == "__main__":
    main()
