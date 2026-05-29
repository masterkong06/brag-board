# Brag Board — Project Context

Family contribution tracker web app. Flask + SQLite, port 5002.

## Current Status

**LIVE on Kemet (woodsandbryant.com/brag) — currently in testing/UAT.**

## Locations

- **HAL (dev):** /home/masterkong/projects/brag_board/ — port 5002
- **Kemet (prod):** brag.woodsandbryant.com — nginx proxy, systemd service

## Stack

- Backend: Python 3.12, Flask
- Database: SQLite (brag_board.db)
- Auth: Werkzeug password hashing, bcrypt
- Frontend: Bootstrap 5.3, vanilla JS
- Server: Gunicorn (multi-worker)
- Process: systemd service
- Proxy: nginx (SSL termination)

## Features Built

- Login/logout, hashed passwords, admin role
- Brag feed with categories (Kitchen, Home, Yard, Pets, Errands, Other)
- Emoji reactions (❤️ 🙌 🔥) via AJAX — toggle on/off, no page reload
- Wishes system — post requests, anyone can claim/fulfill → auto-converts to brag
- Weekly stats (brag count + contributor count for last 7 days)
- Avatar colors, user profiles
- Admin panel: add/delete users, assign avatar colors, set admin role
- /profile page: all users can edit their own display name
- Photo attachments with client-side canvas compression
- Camera vs gallery picker on mobile
- Weekly email digest via Gmail SMTP
- PWA install support + Badge API dot notification

## Known Issues / History

- SECRET_KEY must be set as env var — was previously generating random key per gunicorn worker causing session loss; fixed
- Service file sets SECRET_KEY=bragboard_change_this_in_production (update on Kemet)
- Photo picker had a bug where menu never opened — fixed with explicit block/none toggle

## Deployment

Deployed to Kemet at brag.woodsandbryant.com via GitHub Actions CI/CD.
- Subdomain routing (not sub-path — no ProxyFix needed)
- nginx server block for brag.woodsandbryant.com
- systemd service on Kemet

## Git

- Repo: github.com/masterkong06/brag-board
- Main branch: main
- Workflow: feature branches named after feature, merge to main when done, commit after each successful feature

## Next Steps

- Complete UAT / family testing
- Fix any bugs surfaced during testing
