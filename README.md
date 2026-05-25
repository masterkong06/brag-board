# 🏆 Brag Board

A family contribution tracker — post brags, react to each other's wins, and keep a shared wish list. Built to make household teamwork visible and fun.

## Features

- **Brag feed** — post what you got done, organized by category (Kitchen, Home, Yard, Pets, Errands, Other)
- **Emoji reactions** — react to family members' brags with ❤️ 🙌 🔥 (toggle on/off, AJAX — no page reload)
- **Wish list** — post something you'd like done; anyone can claim it and it auto-converts to a brag
- **Weekly stats** — brag count and contributor count for the last 7 days
- **User profiles** — colored avatars, everyone can edit their own display name
- **Admin panel** — add/remove family members, assign avatar colors, set admin role
- **Secure sessions** — bcrypt-hashed passwords, stable secret key across gunicorn workers

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask |
| Database | SQLite (via Python stdlib `sqlite3`) |
| Auth | Werkzeug `generate_password_hash` / `check_password_hash` |
| Frontend | Bootstrap 5.3, vanilla JS |
| Server | Gunicorn (multi-worker) |
| Process | systemd service |
| Proxy | nginx (SSL termination) |

## Local Development

### Prerequisites

- Python 3.10+
- `git`

### Setup

```bash
git clone git@github.com:masterkong06/brag-board.git
cd brag-board

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run (development)

```bash
export SECRET_KEY=dev-secret-change-me
python app.py
```

Open `http://localhost:5002`. On first run, an `admin` user is created automatically:

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `changeme` |

**Change the password immediately** at `/settings`.

### Database

SQLite database is created automatically at `brag_board.db` on first run. It is excluded from version control via `.gitignore`.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ Yes | Flask session signing key. Must be the same across all gunicorn workers. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |

## Production Deployment

These instructions assume an Ubuntu 24.04 server with nginx and Python 3 already installed.

### 1. Clone the repo

```bash
cd /var/www   # or wherever you prefer
git clone git@github.com:masterkong06/brag-board.git
cd brag-board
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Generate a secret key

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Save the output — you'll use it in the next step.

### 3. Create the systemd service

Copy and edit the included service file:

```bash
sudo cp brag-board.service /etc/systemd/system/brag-board.service
sudo nano /etc/systemd/system/brag-board.service
```

Update `WorkingDirectory`, `ExecStart`, and `SECRET_KEY` to match your paths and generated key:

```ini
[Unit]
Description=Brag Board — Family Contribution Tracker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/brag-board
ExecStart=/var/www/brag-board/venv/bin/gunicorn -w 2 -b 127.0.0.1:5002 app:app
Restart=on-failure
RestartSec=5
Environment=SECRET_KEY=your-generated-secret-key-here

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable brag-board
sudo systemctl start brag-board
sudo systemctl status brag-board
```

### 4. Configure nginx

Create `/etc/nginx/sites-available/brag.yourdomain.com`:

```nginx
server {
    listen 80;
    server_name brag.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name brag.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/brag.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/brag.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and reload:

```bash
sudo ln -s /etc/nginx/sites-available/brag.yourdomain.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. SSL certificate

```bash
sudo certbot --nginx -d brag.yourdomain.com
```

### 6. DNS

Add an `A` record at your registrar:

```
brag.yourdomain.com  →  <your server IP>
```

## CI/CD with GitHub Actions

Deployments are automated on every push to `main`.

### Setup

1. **Generate a deploy key** on your server:
   ```bash
   ssh-keygen -t ed25519 -C "brag-board-deploy" -f ~/.ssh/brag_board_deploy
   ```

2. **Add the public key** to your server's `~/.ssh/authorized_keys`:
   ```bash
   cat ~/.ssh/brag_board_deploy.pub >> ~/.ssh/authorized_keys
   ```

3. **Add GitHub Actions secrets** (Settings → Secrets → Actions):
   | Secret | Value |
   |---|---|
   | `DEPLOY_HOST` | Your server IP or hostname |
   | `DEPLOY_USER` | SSH username (e.g. `linuxuser`) |
   | `DEPLOY_KEY` | Contents of `~/.ssh/brag_board_deploy` (private key) |
   | `DEPLOY_PATH` | Absolute path to the repo on the server (e.g. `/var/www/brag-board`) |

The workflow (`.github/workflows/deploy.yml`) runs on every push to `main`: SSH into the server → `git pull` → `pip install` → `systemctl restart brag-board`.

## Project Structure

```
brag-board/
├── app.py              # Flask routes and app factory
├── auth.py             # Password hashing, login_required / admin_required decorators
├── db.py               # SQLite schema and all database functions
├── requirements.txt    # Python dependencies
├── brag-board.service  # systemd unit file template
├── static/
│   └── style.css       # Custom styles (Bootstrap 5 base)
└── templates/
    ├── base.html       # Navbar, flash messages, Bootstrap CDN
    ├── index.html      # Main brag feed + wish list
    ├── login.html      # Login form
    ├── profile.html    # Edit display name
    └── settings.html   # Admin: add/remove users
```

## License

MIT — see [LICENSE](LICENSE).
