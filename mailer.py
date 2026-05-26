"""
Weekly digest mailer for Brag Board.
Reads SMTP config from environment variables:
  SMTP_USER      — Gmail address (sender)
  SMTP_PASSWORD  — Gmail app password
  SMTP_HOST      — defaults to smtp.gmail.com
  SMTP_PORT      — defaults to 587
  SITE_URL       — defaults to https://brag.woodsandbryant.com
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

import db

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SITE_URL = os.getenv("SITE_URL", "https://brag.woodsandbryant.com")

CATEGORY_LABELS = {
    "kitchen": ("🍽️", "Kitchen"),
    "home":    ("🏡", "Home"),
    "yard":    ("🌿", "Yard"),
    "pets":    ("🐾", "Pets"),
    "errands": ("🛒", "Errands"),
    "other":   ("✨", "Other"),
}


def send_digest():
    """Build and send the weekly digest to all users with email addresses."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("SMTP not configured — set SMTP_USER and SMTP_PASSWORD env vars.")
        return False

    recipients = [u for u in db.get_all_users() if u["email"]]
    if not recipients:
        print("No users have email addresses configured.")
        return False

    data = db.get_weekly_digest_data()
    week_str = date.today().strftime("%B %d, %Y")
    subject = f"🏆 Brag Board — Weekly Digest · {week_str}"
    html = _build_html(data, week_str)

    sent = 0
    for user in recipients:
        try:
            _send_one(user["email"], subject, html)
            print(f"  ✓ Sent to {user['email']}")
            sent += 1
        except Exception as e:
            print(f"  ✗ Failed {user['email']}: {e}")

    print(f"Digest sent to {sent}/{len(recipients)} recipients.")
    return sent > 0


def _send_one(to_email, subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Brag Board <{SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())


def _build_html(data, week_str):
    lb = data["leaderboard"]
    streaks = data["streaks"]
    brags = data["top_brags"]
    granted = data["granted"]

    # ── leaderboard rows ──
    medal = ["🥇", "🥈", "🥉"]
    lb_rows = ""
    for i, u in enumerate(lb[:5]):
        icon = medal[i] if i < 3 else f"{i+1}."
        lb_rows += f"""
        <tr>
          <td style="padding:8px 12px;font-size:15px;">{icon}</td>
          <td style="padding:8px 12px;font-size:15px;font-weight:600;">{u['name']}</td>
          <td style="padding:8px 12px;font-size:15px;text-align:right;">⭐ {u['balance']} pts</td>
        </tr>"""

    # ── streak rows ──
    streak_html = ""
    for s in streaks[:5]:
        flame = "🔥" * min(s["streak"] // 3 + 1, 4)
        streak_html += f'<div style="margin-bottom:6px;font-size:15px;">{flame} <strong>{s["name"]}</strong> — {s["streak"]}-day streak</div>'
    if not streak_html:
        streak_html = '<div style="color:#888;font-size:14px;">No active streaks this week.</div>'

    # ── brag cards ──
    brag_cards = ""
    for b in brags:
        ico, label = CATEGORY_LABELS.get(b["category"], ("✨", "Other"))
        ts = b["created_at"][:10]
        brag_cards += f"""
        <div style="background:#f8f9fa;border-left:4px solid #4361ee;border-radius:6px;
                    padding:10px 14px;margin-bottom:10px;">
          <div style="font-size:13px;color:#666;margin-bottom:4px;">
            <strong>{b['user_name']}</strong> &nbsp;·&nbsp; {ico} {label} &nbsp;·&nbsp; {ts}
          </div>
          <div style="font-size:15px;color:#222;">{b['content']}</div>
        </div>"""
    if not brag_cards:
        brag_cards = '<p style="color:#888;font-size:14px;">No brags this week — get posting! 💪</p>'

    # ── granted wishes ──
    granted_html = ""
    for g in granted:
        granted_html += f'<div style="margin-bottom:6px;font-size:14px;">✅ <strong>{g["claimer_name"]}</strong> took care of: "{g["content"]}"</div>'
    granted_section = f"""
        <h3 style="font-size:16px;color:#2a9d8f;margin:24px 0 10px;">✅ Wishes Granted</h3>
        {granted_html}""" if granted else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr><td style="background:#1a1a2e;border-radius:12px 12px 0 0;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;">🏆</div>
          <h1 style="color:#fff;font-size:22px;margin:8px 0 4px;">Family Brag Board</h1>
          <div style="color:#8e9bb4;font-size:14px;">Weekly Digest · {week_str}</div>
        </td></tr>

        <!-- Hero stats -->
        <tr><td style="background:#fff;padding:24px 32px;border-bottom:1px solid #e9ecef;">
          <div style="text-align:center;">
            <span style="font-size:36px;font-weight:700;color:#4361ee;">{data['brag_count']}</span>
            <div style="color:#666;font-size:14px;margin-top:4px;">
              brag{'s' if data['brag_count'] != 1 else ''} from
              {data['contributor_count']} contributor{'s' if data['contributor_count'] != 1 else ''} this week
            </div>
          </div>
        </td></tr>

        <!-- Body -->
        <tr><td style="background:#fff;padding:24px 32px;border-radius:0 0 12px 12px;">

          <!-- Leaderboard -->
          <h3 style="font-size:16px;color:#1a1a2e;margin:0 0 12px;">⭐ Points Leaderboard</h3>
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e9ecef;border-radius:8px;overflow:hidden;margin-bottom:24px;">
            {lb_rows}
          </table>

          <!-- Streaks -->
          <h3 style="font-size:16px;color:#1a1a2e;margin:0 0 10px;">🔥 Active Streaks</h3>
          <div style="margin-bottom:24px;">{streak_html}</div>

          <!-- Top brags -->
          <h3 style="font-size:16px;color:#1a1a2e;margin:0 0 10px;">💬 This Week's Brags</h3>
          <div style="margin-bottom:24px;">{brag_cards}</div>

          {granted_section}

          <!-- CTA -->
          <div style="text-align:center;margin-top:28px;padding-top:24px;border-top:1px solid #e9ecef;">
            <a href="{SITE_URL}" style="display:inline-block;background:#4361ee;color:#fff;
               text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;">
              View the Board →
            </a>
            <div style="color:#aaa;font-size:12px;margin-top:16px;">
              You're receiving this because you're part of the family board.<br>
              Sent every Sunday morning.
            </div>
          </div>

        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
