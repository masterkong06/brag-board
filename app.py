import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import db
from auth import hash_password, verify_password, login_required, admin_required

app = Flask(__name__)
_secret = os.getenv("SECRET_KEY")
if not _secret:
    raise RuntimeError("SECRET_KEY environment variable must be set")
app.secret_key = _secret

CATEGORIES = [
    ("kitchen",  "🍽️",  "Kitchen"),
    ("home",     "🏡",  "Home"),
    ("yard",     "🌿",  "Yard"),
    ("pets",     "🐾",  "Pets"),
    ("errands",  "🛒",  "Errands"),
    ("other",    "✨",  "Other"),
]
EMOJIS = ["❤️", "🙌", "🔥"]
AVATAR_COLORS = ["#4361ee","#f72585","#7209b7","#3a0ca3","#4cc9f0",
                 "#f4a261","#2a9d8f","#e76f51","#264653","#e9c46a"]


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
    return render_template(
        "index.html",
        brags=brags,
        reactions=reactions,
        wishes=wishes,
        stats=stats,
        categories=CATEGORIES,
        cat_map=cat_map,
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
        db.post_brag(session["user_id"], content, category)
    return redirect(url_for("index"))


@app.route("/brag/<int:brag_id>/delete", methods=["POST"])
@login_required
def delete_brag(brag_id):
    # Users can only delete their own brags; admins can delete any
    if session.get("is_admin") or _brag_owner(brag_id) == session["user_id"]:
        db.delete_brag(brag_id)
    return redirect(url_for("index"))


def _brag_owner(brag_id):
    brags = db.get_brags()
    for b in brags:
        if b["id"] == brag_id:
            return b["user_id"]
    return None


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
    return redirect(url_for("index"))


@app.route("/wish/<int:wish_id>/delete", methods=["POST"])
@login_required
def delete_wish(wish_id):
    wish = db.get_wish(wish_id)
    if wish and (session.get("is_admin") or wish["user_id"] == session["user_id"]):
        db.delete_wish(wish_id)
    return redirect(url_for("index") + "#wishes")


# ---------------------------------------------------------------------------
# Profile (all users)
# ---------------------------------------------------------------------------

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        new_name = request.form.get("name", "").strip()
        if new_name:
            db.update_user_name(session["user_id"], new_name)
            session["user_name"] = new_name
            flash("Display name updated!", "success")
        else:
            flash("Name can't be empty.", "danger")
        return redirect(url_for("profile"))
    return render_template("profile.html")


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


# ---------------------------------------------------------------------------
# Bootstrap — runs under both gunicorn and `python app.py`
# ---------------------------------------------------------------------------

db.init_db()
_seed_admin()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=False)
