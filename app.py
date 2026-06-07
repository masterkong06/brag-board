import os
import uuid
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
import db
import badges as badge_engine
import mailer
from auth import hash_password, verify_password, login_required, admin_required

try:
    from pywebpush import webpush, WebPushException
    _PUSH_AVAILABLE = True
except ImportError:
    _PUSH_AVAILABLE = False

app = Flask(__name__)
_secret = os.getenv("SECRET_KEY")
if not _secret:
    import sys
    _secret = secrets.token_hex(32)
    print("\n  WARNING: SECRET_KEY not set -- using a random key.", file=sys.stderr)
    print("  Sessions will not survive restarts. Set SECRET_KEY for production.\n", file=sys.stderr)
app.secret_key = _secret
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload limit

VAPID_CLAIMS = {"sub": "mailto:support@simianllc.com"}


def _get_vapid_keys():
    """Return (private_b64url_der, public_b64url) — generate and persist on first call.

    Private key is stored as base64url(DER) — the format py_vapid.Vapid.from_string()
    expects. Public key is base64url of the uncompressed EC point (what browsers need).
    """
    pub = db.get_app_setting("vapid_public_key")
    priv = db.get_app_setting("vapid_private_key")
    if pub and priv and not priv.startswith("-----"):
        return priv, pub
    if not _PUSH_AVAILABLE:
        return None, None
    from py_vapid import Vapid
    import base64
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
    v = Vapid()
    v.generate_keys()
    # Store private key as base64url(DER-PKCS8) — what Vapid.from_string() expects
    priv_bytes = v._private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    priv_b64 = base64.urlsafe_b64encode(priv_bytes).rstrip(b"=").decode()
    pub_bytes = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    db.set_app_setting("vapid_private_key", priv_b64)
    db.set_app_setting("vapid_public_key", pub_b64)
    return priv_b64, pub_b64


def _send_push_to_all(title, body):
    """Fire push notifications to all subscribed devices."""
    if not _PUSH_AVAILABLE:
        return
    priv_pem, _ = _get_vapid_keys()
    if not priv_pem:
        return
    import json, logging
    payload = json.dumps({"title": title, "body": body})
    for sub in db.get_all_push_subscriptions():
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                },
                data=payload,
                vapid_private_key=priv_pem,
                vapid_claims=VAPID_CLAIMS,
            )
        except WebPushException as e:
            logging.error("WebPushException for endpoint %s: %s", sub["endpoint"][:40], e)
            if e.response and e.response.status_code in (404, 410):
                db.delete_push_subscription(sub["endpoint"])
        except Exception as e:
            logging.error("Push error for endpoint %s: %s", sub["endpoint"][:40], e)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
PROFILE_PHOTO_FOLDER = os.path.join(UPLOAD_FOLDER, "profiles")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_PHOTO_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

CATEGORIES = [
    ("kitchen",  "🍽️",  "Kitchen"),
    ("home",     "🏡",  "Home"),
    ("yard",     "🌿",  "Yard"),
    ("pets",     "🐾",  "Pets"),
    ("errands",  "🛒",  "Errands"),
    ("other",    "✨",  "Other"),
]
EMOJIS = ["❤️", "🙌", "🔥"]
THEMES = [
    ("cobalt-sky",         "#4A9EFF", "Cobalt Sky"),
    ("golden-taupe",       "#7A5900", "Golden Taupe"),
    ("beachfront-views",   "#156285", "Beachfront Views"),
    ("under-the-moonlight","#B0A8D8", "Under the Moonlight"),
    ("minty-fresh",        "#0C5C37", "Minty Fresh"),
    ("frozen-lake",        "#0E4A84", "Frozen Lake"),
    ("autumn-orchard",     "#8B3500", "Autumn Orchard"),
    ("harvest-moon",       "#F4A832", "Harvest Moon"),
    ("chili-spice",        "#FF6040", "Chili Spice"),
    ("wisteria-bloom",     "#6A1B9A", "Wisteria Bloom"),
    ("zesty-lemon",        "#7A6200", "Zesty Lemon"),
    ("mango-popsicle",     "#A03C00", "Mango Popsicle"),
]
AVATAR_COLORS = ["#4361ee","#f72585","#7209b7","#3a0ca3","#4cc9f0",
                 "#f4a261","#2a9d8f","#e76f51","#264653","#e9c46a"]


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_upload(file_obj):
    """Save an uploaded FileStorage object; return filename or None."""
    if not file_obj or not file_obj.filename:
        return None
    if not _allowed_file(file_obj.filename):
        return None
    ext = secure_filename(file_obj.filename).rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_obj.save(os.path.join(UPLOAD_FOLDER, filename))
    return filename


def _delete_upload(filename):
    """Remove an uploaded file from disk if it exists."""
    if filename:
        path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def _seed_admin():
    if db.user_count() == 0:
        pw = "changeme"
        db.create_user(
            name="Admin",
            username="admin",
            password_hash=hash_password(pw),
            color=AVATAR_COLORS[0],
            is_admin=1,
        )
        print(f"\n  ✅  First-run: created admin user")
        print(f"      username: admin")
        print(f"      password: {pw}")
        print(f"      Change it at /settings after logging in.\n")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = db.get_user_by_username(username)
        if user and verify_password(password, user["password_hash"]):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["username"] = user["username"]
            session["user_color"] = user["color"]
            session["is_admin"] = bool(user["is_admin"])
            session["user_photo"] = user["profile_photo"]
            session["user_theme"] = user["theme"] or "cobalt-sky"
            return redirect(url_for("index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Main feed
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def index():
    brags = db.get_brags()
    brag_ids = [b["id"] for b in brags]
    reactions = db.get_reactions_for_brags(brag_ids)
    wishes = db.get_wishes()
    stats = db.weekly_stats()
    cat_map = {k: (ico, label) for k, ico, label in CATEGORIES}
    cat_pts    = db.get_category_points()
    my_balance = db.get_user_points_balance(session["user_id"])
    my_streak  = db.get_user_streak(session["user_id"])
    all_badges = db.get_all_user_badges()
    return render_template(
        "index.html",
        brags=brags,
        reactions=reactions,
        wishes=wishes,
        stats=stats,
        categories=CATEGORIES,
        cat_map=cat_map,
        cat_pts=cat_pts,
        my_balance=my_balance,
        my_streak=my_streak,
        all_badges=all_badges,
        badge_map=badge_engine.BADGE_MAP,
        emojis=EMOJIS,
        current_user_id=session["user_id"],
        current_user_name=session["user_name"],
    )


@app.route("/brag", methods=["POST"])
@login_required
def post_brag():
    content = request.form.get("content", "").strip()
    category = request.form.get("category", "other")
    if content:
        photo_filename = _save_upload(request.files.get("photo"))
        db.post_brag(session["user_id"], content, category, photo_filename)
        newly = badge_engine.check_and_award(session["user_id"])
        for b in newly:
            flash(f"{b['emoji']} New badge unlocked: <strong>{b['name']}</strong> — {b['desc']}", "success")
        _send_push_to_all(
            f"{session['user_name']} shared something!",
            content[:120] + ("…" if len(content) > 120 else ""),
        )
    return redirect(url_for("index"))


@app.route("/sw.js")
def service_worker():
    response = app.send_static_file("sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/push/vapid-public-key")
@login_required
def push_vapid_public_key():
    _, pub = _get_vapid_keys()
    if not pub:
        return jsonify({"error": "push not configured"}), 503
    return jsonify({"key": pub})


@app.route("/push/subscribe", methods=["POST"])
@login_required
def push_subscribe():
    data = request.get_json()
    if not data:
        return jsonify({"error": "bad request"}), 400
    endpoint = data.get("endpoint", "")
    p256dh = data.get("keys", {}).get("p256dh", "")
    auth = data.get("keys", {}).get("auth", "")
    if not (endpoint and p256dh and auth):
        return jsonify({"error": "missing fields"}), 400
    db.upsert_push_subscription(session["user_id"], endpoint, p256dh, auth)
    return jsonify({"ok": True})


@app.route("/push/unsubscribe", methods=["POST"])
@login_required
def push_unsubscribe():
    data = request.get_json()
    if data and data.get("endpoint"):
        db.delete_push_subscription(data["endpoint"])
    return jsonify({"ok": True})


@app.route("/push/test", methods=["POST"])
@admin_required
def push_test():
    subs = db.get_all_push_subscriptions()
    _send_push_to_all("Test notification", f"Push is working! ({len(subs)} subscriber(s))")
    return jsonify({"ok": True, "subscribers": len(subs)})


@app.route("/brag/<int:brag_id>/edit", methods=["POST"])
@login_required
def edit_brag(brag_id):
    brag = db.get_brag_by_id(brag_id)
    if brag and brag["user_id"] == session["user_id"]:
        content = request.form.get("content", "").strip()
        category = request.form.get("category", brag["category"])
        if content:
            db.update_brag(brag_id, content, category)
    return redirect(url_for("index"))


@app.route("/brag/<int:brag_id>/delete", methods=["POST"])
@login_required
def delete_brag(brag_id):
    brag = db.get_brag_by_id(brag_id)
    if brag and brag["user_id"] == session["user_id"]:
        db.delete_brag(brag_id)
        _delete_upload(brag["photo_filename"])
    return redirect(url_for("index"))



# ---------------------------------------------------------------------------
# Reactions (AJAX)
# ---------------------------------------------------------------------------

@app.route("/react/<int:brag_id>", methods=["POST"])
@login_required
def react(brag_id):
    emoji = request.json.get("emoji")
    if not emoji or emoji not in EMOJIS:
        return jsonify({"error": "invalid emoji"}), 400
    added = db.toggle_reaction(brag_id, session["user_id"], emoji)
    summary = db.reaction_summary(brag_id)
    return jsonify({"added": added, "summary": summary})


# ---------------------------------------------------------------------------
# Wishes
# ---------------------------------------------------------------------------

@app.route("/wish", methods=["POST"])
@login_required
def add_wish():
    content = request.form.get("content", "").strip()
    if content:
        db.add_wish(session["user_id"], content)
    return redirect(url_for("index") + "#wishes")


@app.route("/wish/<int:wish_id>/claim", methods=["POST"])
@login_required
def claim_wish(wish_id):
    category = request.form.get("category", "other")
    db.claim_wish(wish_id, session["user_id"], category)
    newly = badge_engine.check_and_award(session["user_id"])
    for b in newly:
        flash(f"{b['emoji']} New badge unlocked: <strong>{b['name']}</strong> — {b['desc']}", "success")
    return redirect(url_for("index"))


@app.route("/wish/<int:wish_id>/delete", methods=["POST"])
@login_required
def delete_wish(wish_id):
    wish = db.get_wish(wish_id)
    if wish and (session.get("is_admin") or wish["user_id"] == session["user_id"]):
        db.delete_wish(wish_id)
    return redirect(url_for("index") + "#wishes")


# ---------------------------------------------------------------------------
# Rewards (all users — view & redeem; admin — manage)
# ---------------------------------------------------------------------------

@app.route("/rewards")
@login_required
def rewards():
    rewards_list  = db.get_active_rewards()
    cat_pts       = db.get_category_points()
    balance       = db.get_user_points_balance(session["user_id"])
    my_redemptions = db.get_user_redemptions(session["user_id"])
    leaderboard   = db.get_all_balances()
    pending       = db.get_pending_redemptions() if session.get("is_admin") else []
    all_rewards   = db.get_all_rewards()         if session.get("is_admin") else []
    denial_cooldown = int(db.get_app_setting("denial_cooldown_hours", 24))
    return render_template(
        "rewards.html",
        rewards=rewards_list,
        cat_pts=cat_pts,
        balance=balance,
        my_redemptions=my_redemptions,
        leaderboard=leaderboard,
        pending=pending,
        all_rewards=all_rewards,
        categories=CATEGORIES,
        denial_cooldown=denial_cooldown,
    )


@app.route("/rewards/redeem/<int:reward_id>", methods=["POST"])
@login_required
def redeem_reward(reward_id):
    reward = next((r for r in db.get_active_rewards() if r["id"] == reward_id), None)
    if not reward:
        flash("Reward not found.", "danger")
        return redirect(url_for("rewards"))
    balance = db.get_user_points_balance(session["user_id"])
    if balance < reward["points_cost"]:
        flash("Not enough points for that reward.", "danger")
        return redirect(url_for("rewards"))
    remaining = db.get_denial_cooldown_remaining(session["user_id"], reward_id)
    if remaining > 0:
        hrs = int(remaining) + 1
        flash(f"This redemption was recently denied. Try again in {hrs} hour{'s' if hrs != 1 else ''}.", "warning")
        return redirect(url_for("rewards"))
    db.request_redemption(session["user_id"], reward_id)
    flash(f"Redemption request sent for '{reward['name']}'! Waiting for approval.", "success")
    return redirect(url_for("rewards"))


@app.route("/rewards/resolve/<int:redemption_id>/<status>", methods=["POST"])
@admin_required
def resolve_redemption(redemption_id, status):
    if status not in ("approved", "denied"):
        return redirect(url_for("rewards"))
    db.resolve_redemption(redemption_id, status, session["user_id"])
    flash(f"Redemption {status}.", "success")
    return redirect(url_for("rewards") + "#admin")


@app.route("/rewards/create", methods=["POST"])
@admin_required
def create_reward():
    name        = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    points_cost = request.form.get("points_cost", "0")
    try:
        points_cost = int(points_cost)
        assert points_cost > 0
    except (ValueError, AssertionError):
        flash("Points cost must be a positive number.", "danger")
        return redirect(url_for("rewards") + "#admin")
    if name:
        db.create_reward(name, description, points_cost, session["user_id"])
        flash(f"Reward '{name}' created.", "success")
    return redirect(url_for("rewards") + "#admin")


@app.route("/rewards/settings", methods=["POST"])
@admin_required
def update_reward_settings():
    hours = request.form.get("denial_cooldown_hours", "24")
    try:
        hours = max(0, int(hours))
    except ValueError:
        hours = 24
    db.set_app_setting("denial_cooldown_hours", hours)
    flash("Reward settings saved.", "success")
    return redirect(url_for("rewards") + "#admin")


@app.route("/rewards/toggle/<int:reward_id>", methods=["POST"])
@admin_required
def toggle_reward(reward_id):
    db.toggle_reward_active(reward_id)
    return redirect(url_for("rewards") + "#admin")


@app.route("/rewards/points", methods=["POST"])
@admin_required
def update_category_points():
    for key, ico, label in CATEGORIES:
        val = request.form.get(f"pts_{key}", "")
        try:
            pts = int(val)
            if pts >= 0:
                db.set_category_points(key, pts)
        except ValueError:
            pass
    flash("Point values updated.", "success")
    return redirect(url_for("rewards") + "#admin")


# ---------------------------------------------------------------------------
# Profile (all users)
# ---------------------------------------------------------------------------

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = session["user_id"]
    if request.method == "POST":
        action = request.form.get("action", "name")

        if action == "name":
            new_name = request.form.get("name", "").strip()
            if new_name:
                db.update_user_name(uid, new_name)
                session["user_name"] = new_name
                flash("Display name updated!", "success")
            else:
                flash("Name can't be empty.", "danger")

        elif action == "password":
            current_pw  = request.form.get("current_password", "")
            new_pw      = request.form.get("new_password", "").strip()
            confirm_pw  = request.form.get("confirm_password", "").strip()
            user_row    = db.get_user_by_id(uid)
            if not verify_password(current_pw, user_row["password_hash"]):
                flash("Current password is incorrect.", "danger")
            elif len(new_pw) < 6:
                flash("New password must be at least 6 characters.", "danger")
            elif new_pw != confirm_pw:
                flash("Passwords don't match.", "danger")
            else:
                db.update_user_password(uid, hash_password(new_pw))
                flash("Password updated!", "success")

        elif action == "theme":
            theme = request.form.get("theme", "cobalt-sky")
            if theme in {t[0] for t in THEMES}:
                db.update_user_theme(uid, theme)
                session["user_theme"] = theme

        elif action == "photo":
            file_obj = request.files.get("photo")
            if file_obj and file_obj.filename and _allowed_file(file_obj.filename):
                ext = secure_filename(file_obj.filename).rsplit(".", 1)[-1].lower()
                filename = f"profile_{uid}_{uuid.uuid4().hex[:8]}.{ext}"
                file_obj.save(os.path.join(PROFILE_PHOTO_FOLDER, filename))
                old_user = db.get_user_by_id(uid)
                if old_user["profile_photo"]:
                    try:
                        os.remove(os.path.join(PROFILE_PHOTO_FOLDER, old_user["profile_photo"]))
                    except FileNotFoundError:
                        pass
                db.update_user_photo(uid, filename)
                session["user_photo"] = filename
                flash("Profile photo updated!", "success")
            else:
                flash("Invalid file — use jpg, png, gif, or webp.", "danger")

        return redirect(url_for("profile"))

    user_row      = db.get_user_by_id(uid)
    my_badges     = db.get_user_badges(uid)
    my_streak     = db.get_user_streak(uid)
    longest       = db.get_user_longest_streak(uid)
    my_balance    = db.get_user_points_balance(uid)
    all_badge_def = badge_engine.BADGES
    held_slugs    = {b["badge_slug"] for b in my_badges}
    return render_template(
        "profile.html",
        user=user_row,
        my_badges=my_badges,
        my_streak=my_streak,
        longest_streak=longest,
        my_balance=my_balance,
        all_badges=all_badge_def,
        held_slugs=held_slugs,
        badge_map=badge_engine.BADGE_MAP,
        themes=THEMES,
    )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@app.route("/settings")
@admin_required
def settings():
    users = db.get_all_users()
    return render_template("settings.html", users=users,
                           colors=AVATAR_COLORS)


@app.route("/settings/add-user", methods=["POST"])
@admin_required
def add_user():
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "").strip()
    color = request.form.get("color", AVATAR_COLORS[0])
    is_admin = 1 if request.form.get("is_admin") else 0
    if name and username and password:
        try:
            db.create_user(name, username, hash_password(password), color, is_admin)
            flash(f"Added {name}.", "success")
        except Exception:
            flash(f"Username '{username}' is already taken.", "danger")
    else:
        flash("All fields are required.", "danger")
    return redirect(url_for("settings"))


@app.route("/settings/delete-user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("You can't delete yourself.", "danger")
    else:
        db.delete_user(user_id)
        flash("User removed.", "success")
    return redirect(url_for("settings"))


@app.route("/settings/update-email/<int:user_id>", methods=["POST"])
@admin_required
def update_email(user_id):
    email = request.form.get("email", "").strip().lower()
    db.update_user_email(user_id, email or None)
    flash("Email updated.", "success")
    return redirect(url_for("settings"))


@app.route("/admin/send-digest", methods=["POST"])
@admin_required
def send_digest():
    ok = mailer.send_digest()
    if ok:
        flash("Weekly digest sent! ✉️", "success")
    else:
        flash("Digest failed — check SMTP config or email addresses in Settings.", "danger")
    return redirect(url_for("settings"))


import re

def _extract_youtube_id(url):
    """Extract video ID from various YouTube URL formats."""
    if not url:
        return None
    url = url.strip()
    patterns = [
        r'(?:v=|/embed/|youtu\.be/)([A-Za-z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    # bare ID?
    if re.match(r'^[A-Za-z0-9_-]{11}$', url):
        return url
    return None


# ---------------------------------------------------------------------------
# Learn Hub
# ---------------------------------------------------------------------------

@app.route("/learn")
@login_required
def learn():
    all_cats   = db.learn_get_categories()
    buckets    = [c for c in all_cats if c["parent_id"] is None]
    subcats    = [c for c in all_cats if c["parent_id"] is not None]

    bucket_id  = request.args.get("bucket", type=int)
    cat_id     = request.args.get("cat", type=int)

    if cat_id:
        tasks = db.learn_get_tasks(category_id=cat_id)
        # Ensure the parent bucket stays highlighted
        parent = next((c for c in subcats if c["id"] == cat_id), None)
        if parent and not bucket_id:
            bucket_id = parent["parent_id"]
    elif bucket_id:
        tasks = db.learn_get_tasks_for_bucket(bucket_id)
    else:
        tasks = db.learn_get_tasks()

    active_subcats = [c for c in subcats if c["parent_id"] == bucket_id] if bucket_id else []
    completions = db.learn_get_user_completions(session["user_id"])
    return render_template(
        "learn.html",
        categories=all_cats,
        buckets=buckets,
        subcats=subcats,
        active_subcats=active_subcats,
        tasks=tasks,
        completions=completions,
        active_bucket=bucket_id,
        active_cat=cat_id,
    )


@app.route("/learn/<int:task_id>")
@login_required
def learn_task(task_id):
    task = db.learn_get_task(task_id)
    if not task:
        return redirect(url_for("learn"))
    questions = db.learn_get_quiz_questions(task_id)
    watch = db.learn_get_watch_session(session["user_id"], task_id)
    completions = db.learn_get_user_completions(session["user_id"])
    settings = db.learn_get_settings()
    threshold = task["watch_threshold_pct"]
    watched_pct = watch["pct_watched"] if watch else 0
    quiz_unlocked = watched_pct >= threshold
    prior_completions = completions.get(task_id, [])
    return render_template(
        "learn_task.html",
        task=task,
        questions=questions,
        settings=settings,
        watched_pct=watched_pct,
        quiz_unlocked=quiz_unlocked,
        prior_completions=prior_completions,
    )


@app.route("/learn/<int:task_id>/watch", methods=["POST"])
@login_required
def learn_watch(task_id):
    pct = request.json.get("pct", 0)
    pct = max(0, min(100, int(pct)))
    db.learn_upsert_watch(session["user_id"], task_id, pct)
    task = db.learn_get_task(task_id)
    threshold = task["watch_threshold_pct"] if task else 80
    return jsonify({"ok": True, "unlocked": pct >= threshold})


@app.route("/learn/<int:task_id>/complete", methods=["POST"])
@login_required
def learn_complete(task_id):
    """Submit quiz answers (optional) and post a brag to earn bonus points."""
    task = db.learn_get_task(task_id)
    if not task:
        return redirect(url_for("learn"))

    settings = db.learn_get_settings()
    questions = db.learn_get_quiz_questions(task_id)
    brag_content = request.form.get("brag_content", "").strip()
    if not brag_content:
        flash("Add a note about what you took on before sharing.", "warning")
        return redirect(url_for("learn_task", task_id=task_id))

    # Score quiz if questions exist
    quiz_score = None
    if questions:
        correct = 0
        for q in questions:
            answer = request.form.get(f"q{q['id']}", "")
            if answer.lower() == q["correct_choice"].lower():
                correct += 1
        quiz_score = correct

    # Determine bonus
    is_first = db.learn_is_first_completion(session["user_id"], task_id)
    if is_first and questions and quiz_score is not None:
        pass_threshold = int(settings.get("quiz_pass_threshold", 2))
        pass_mult  = int(settings.get("quiz_pass_multiplier", 100))
        part_mult  = int(settings.get("quiz_partial_multiplier", 40))
        fail_mult  = int(settings.get("quiz_fail_multiplier", 15))
        base = task["bonus_points_first"]
        if quiz_score >= pass_threshold:
            mult = pass_mult
        elif quiz_score == pass_threshold - 1:
            mult = part_mult
        else:
            mult = fail_mult
        bonus = round(base * mult / 100)
    elif is_first:
        bonus = task["bonus_points_first"]
    else:
        bonus = task["bonus_points_repeat"]

    # Post the brag and award bonus via a special category
    brag_id = db.post_brag(
        session["user_id"],
        brag_content,
        category=task["cat_name"].lower().replace(" ", "_"),
    )
    # Award bonus by inserting a completion record (points summed from learn_completions)
    db.learn_record_completion(session["user_id"], task_id, quiz_score, bonus, brag_id)

    # Check badges
    newly = badge_engine.check_and_award(session["user_id"])

    if quiz_score is not None:
        score_msg = f"{quiz_score}/{len(questions)} on the quiz"
    else:
        score_msg = "no quiz"

    flash(
        f"🎉 Brag logged! You earned <strong>+{bonus} bonus pts</strong> ({score_msg}).",
        "success",
    )
    return redirect(url_for("index"))


# ----- Admin: Learn categories -----

@app.route("/learn/admin")
@admin_required
def learn_admin():
    categories   = db.learn_get_all_categories()
    tasks        = db.learn_get_all_tasks()
    settings     = db.learn_get_settings()
    suggestions  = db.learn_get_suggestions(status="pending")
    return render_template("learn_admin.html",
                           categories=categories, tasks=tasks,
                           settings=settings, suggestions=suggestions)


@app.route("/learn/admin/category/new", methods=["POST"])
@admin_required
def learn_admin_new_category():
    name      = request.form.get("name", "").strip()
    emoji     = request.form.get("emoji", "📚").strip() or "📚"
    order     = int(request.form.get("display_order", 0))
    parent_id = request.form.get("parent_id") or None
    if parent_id:
        parent_id = int(parent_id)
    if name:
        db.learn_create_category(name, emoji, order, parent_id=parent_id)
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/category/<int:cat_id>/edit", methods=["POST"])
@admin_required
def learn_admin_edit_category(cat_id):
    parent_id = request.form.get("parent_id") or None
    if parent_id:
        parent_id = int(parent_id)
    is_active = int(request.form.get("is_active", 1))
    db.learn_update_category(
        cat_id,
        request.form.get("name", "").strip(),
        request.form.get("emoji", "📚").strip() or "📚",
        int(request.form.get("display_order", 0)),
        parent_id=parent_id,
        is_active=is_active,
    )
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/category/<int:cat_id>/toggle", methods=["POST"])
@admin_required
def learn_admin_toggle_category(cat_id):
    db.learn_toggle_category(cat_id)
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/category/<int:cat_id>/delete", methods=["POST"])
@admin_required
def learn_admin_delete_category(cat_id):
    db.learn_delete_category(cat_id)
    return redirect(url_for("learn_admin"))


# ----- Admin: Learn tasks -----

@app.route("/learn/admin/task/new", methods=["POST"])
@admin_required
def learn_admin_new_task():
    title    = request.form.get("title", "").strip()
    desc     = request.form.get("description", "").strip()
    cat_id   = int(request.form.get("category_id", 0))
    yt_url   = request.form.get("youtube_url", "").strip()
    yt_id    = _extract_youtube_id(yt_url)
    b_first  = int(request.form.get("bonus_first", 50))
    b_repeat = int(request.form.get("bonus_repeat", 10))
    thresh   = int(request.form.get("threshold", 80))
    if title and cat_id:
        task_id = db.learn_create_task(title, desc, cat_id, yt_id, b_first, b_repeat, thresh)
        # Add quiz questions if provided
        for i in range(1, 4):
            q = request.form.get(f"q{i}_question", "").strip()
            a = request.form.get(f"q{i}_a", "").strip()
            b_ = request.form.get(f"q{i}_b", "").strip()
            c = request.form.get(f"q{i}_c", "").strip()
            d = request.form.get(f"q{i}_d", "").strip()
            correct = request.form.get(f"q{i}_correct", "").strip().lower()
            if q and a and b_ and c and d and correct in ("a","b","c","d"):
                db.learn_add_question(task_id, q, a, b_, c, d, correct)
        flash(f"Task '{title}' created.", "success")
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/task/<int:task_id>/toggle", methods=["POST"])
@admin_required
def learn_admin_toggle_task(task_id):
    task = db.learn_get_task(task_id)
    if task:
        db.learn_update_task(
            task_id, task["title"], task["description"], task["category_id"],
            task["youtube_video_id"], task["bonus_points_first"],
            task["bonus_points_repeat"], task["watch_threshold_pct"],
            1 - task["is_active"],
        )
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/task/<int:task_id>/delete", methods=["POST"])
@admin_required
def learn_admin_delete_task(task_id):
    db.learn_delete_task(task_id)
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/task/<int:task_id>/question/new", methods=["POST"])
@admin_required
def learn_admin_new_question(task_id):
    q       = request.form.get("question", "").strip()
    a       = request.form.get("choice_a", "").strip()
    b_      = request.form.get("choice_b", "").strip()
    c       = request.form.get("choice_c", "").strip()
    d       = request.form.get("choice_d", "").strip()
    correct = request.form.get("correct_choice", "").strip().lower()
    if q and a and b_ and c and d and correct in ("a","b","c","d"):
        db.learn_add_question(task_id, q, a, b_, c, d, correct)
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/question/<int:q_id>/delete", methods=["POST"])
@admin_required
def learn_admin_delete_question(q_id):
    db.learn_delete_question(q_id)
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/settings", methods=["POST"])
@admin_required
def learn_admin_settings():
    for key in ("watch_threshold_pct","bonus_first_watch","bonus_repeat_watch",
                "quiz_pass_threshold","quiz_pass_multiplier",
                "quiz_partial_multiplier","quiz_fail_multiplier"):
        val = request.form.get(key, "").strip()
        if val.isdigit():
            db.learn_set_setting(key, val)
    flash("Learn Hub settings saved.", "success")
    return redirect(url_for("learn_admin"))


@app.route("/learn/admin/suggestion/<int:s_id>/resolve", methods=["POST"])
@admin_required
def learn_admin_resolve_suggestion(s_id):
    status = request.form.get("status", "rejected")
    if status in ("approved", "rejected"):
        db.learn_resolve_suggestion(s_id, status)
    return redirect(url_for("learn_admin"))


@app.route("/learn/suggest", methods=["POST"])
@login_required
def learn_suggest():
    title   = request.form.get("title", "").strip()
    desc    = request.form.get("description", "").strip()
    cat_id  = request.form.get("category_id") or None
    if cat_id:
        cat_id = int(cat_id)
    if title:
        db.learn_submit_suggestion(session["user_id"], title, desc, cat_id)
        flash("Thanks! Your suggestion has been submitted for review.", "success")
    return redirect(url_for("learn"))


# ---------------------------------------------------------------------------
# Bootstrap — runs under both gunicorn and `python app.py`
# ---------------------------------------------------------------------------

db.init_db()
db.seed_category_points()
db.learn_seed_settings()
db.learn_seed_buckets()
_seed_admin()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
