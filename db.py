import sqlite3
import os
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "brag_board.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#6c757d',
    is_admin INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS brags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    category TEXT DEFAULT 'other',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brag_id INTEGER NOT NULL REFERENCES brags(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    emoji TEXT NOT NULL,
    UNIQUE(brag_id, user_id, emoji)
);

CREATE TABLE IF NOT EXISTS wishes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    fulfilled_by_brag_id INTEGER REFERENCES brags(id),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_badges (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    badge_slug TEXT NOT NULL,
    awarded_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, badge_slug)
);

CREATE TABLE IF NOT EXISTS category_points (
    category TEXT PRIMARY KEY,
    points INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    points_cost INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS redemptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    reward_id INTEGER NOT NULL REFERENCES rewards(id),
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | denied
    requested_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    resolved_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS learn_categories (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    emoji         TEXT NOT NULL DEFAULT '📚',
    display_order INTEGER NOT NULL DEFAULT 0,
    parent_id     INTEGER REFERENCES learn_categories(id),
    is_active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS learn_tasks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    description         TEXT DEFAULT '',
    category_id         INTEGER NOT NULL REFERENCES learn_categories(id),
    youtube_video_id    TEXT,
    bonus_points_first  INTEGER NOT NULL DEFAULT 50,
    bonus_points_repeat INTEGER NOT NULL DEFAULT 10,
    watch_threshold_pct INTEGER NOT NULL DEFAULT 80,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS learn_quiz_questions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id        INTEGER NOT NULL REFERENCES learn_tasks(id),
    question       TEXT NOT NULL,
    choice_a       TEXT NOT NULL,
    choice_b       TEXT NOT NULL,
    choice_c       TEXT NOT NULL,
    choice_d       TEXT NOT NULL,
    correct_choice TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learn_watch_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    task_id     INTEGER NOT NULL REFERENCES learn_tasks(id),
    pct_watched INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, task_id)
);

CREATE TABLE IF NOT EXISTS learn_completions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    task_id      INTEGER NOT NULL REFERENCES learn_tasks(id),
    quiz_score   INTEGER,
    bonus_awarded INTEGER NOT NULL DEFAULT 0,
    brag_id      INTEGER REFERENCES brags(id),
    completed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS learn_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learn_task_suggestions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    category_id INTEGER REFERENCES learn_categories(id),
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    endpoint    TEXT NOT NULL UNIQUE,
    p256dh      TEXT NOT NULL,
    auth        TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with _conn() as conn:
        conn.executescript(SCHEMA)
        # Migration: add photo_filename to brags (safe to run repeatedly)
        try:
            conn.execute("ALTER TABLE brags ADD COLUMN photo_filename TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists
        # Migration: add email to users
        try:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        except sqlite3.OperationalError:
            pass
        # Migration: add profile_photo to users
        try:
            conn.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
        except sqlite3.OperationalError:
            pass
        # Migration: add theme preference to users
        try:
            conn.execute("ALTER TABLE users ADD COLUMN theme TEXT NOT NULL DEFAULT 'cobalt-sky'")
        except sqlite3.OperationalError:
            pass
        # Migration: rename learn_tasks bonus columns (short → long names)
        for old, new in [("bonus_pts_first", "bonus_points_first"),
                         ("bonus_pts_repeat", "bonus_points_repeat")]:
            try:
                conn.execute(f"ALTER TABLE learn_tasks RENAME COLUMN {old} TO {new}")
            except sqlite3.OperationalError:
                pass
        # Migration: app_settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)
        """)
        conn.execute(
            "INSERT OR IGNORE INTO app_settings (key,value) VALUES ('denial_cooldown_hours','24')"
        )
        # Migration: push subscriptions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                endpoint TEXT NOT NULL UNIQUE,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # Migrations: Learn Hub tables (safe to run repeatedly via CREATE IF NOT EXISTS)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS learn_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                emoji TEXT NOT NULL DEFAULT '📚', display_order INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS learn_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
                description TEXT DEFAULT '', category_id INTEGER NOT NULL,
                youtube_video_id TEXT, bonus_pts_first INTEGER NOT NULL DEFAULT 50,
                bonus_pts_repeat INTEGER NOT NULL DEFAULT 10,
                watch_threshold_pct INTEGER NOT NULL DEFAULT 80,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS learn_quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL,
                question TEXT NOT NULL, choice_a TEXT NOT NULL, choice_b TEXT NOT NULL,
                choice_c TEXT NOT NULL, choice_d TEXT NOT NULL, correct_choice TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learn_watch_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL, pct_watched INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT (datetime('now')), UNIQUE(user_id, task_id)
            );
            CREATE TABLE IF NOT EXISTS learn_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL, quiz_score INTEGER,
                bonus_awarded INTEGER NOT NULL DEFAULT 0, brag_id INTEGER,
                completed_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS learn_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS learn_task_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL, description TEXT DEFAULT '',
                category_id INTEGER REFERENCES learn_categories(id),
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migration: life-skills category columns
        for col, defn in [
            ("parent_id", "INTEGER REFERENCES learn_categories(id)"),
            ("is_active",  "INTEGER NOT NULL DEFAULT 1"),
        ]:
            try:
                conn.execute(f"ALTER TABLE learn_categories ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass  # column already exists


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_user_by_username(username):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def get_user_by_id(user_id):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def get_all_users():
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM users ORDER BY name"
        ).fetchall()


def create_user(name, username, password_hash, color="#6c757d", is_admin=0):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO users (name, username, password_hash, color, is_admin) VALUES (?, ?, ?, ?, ?)",
            (name, username, password_hash, color, is_admin),
        )


def delete_user(user_id):
    with _conn() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def update_user_name(user_id, new_name):
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET name = ? WHERE id = ?",
            (new_name, user_id),
        )


def update_user_email(user_id, email):
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET email = ? WHERE id = ?",
            (email or None, user_id),
        )


def update_user_theme(user_id, theme):
    with _conn() as conn:
        conn.execute("UPDATE users SET theme=? WHERE id=?", (theme, user_id))


def update_user_photo(user_id, filename):
    with _conn() as conn:
        conn.execute("UPDATE users SET profile_photo=? WHERE id=?", (filename, user_id))


def update_user_password(user_id, new_hash):
    with _conn() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))


def get_user_by_id(user_id):
    with _conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def user_count():
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


# ---------------------------------------------------------------------------
# Brags
# ---------------------------------------------------------------------------

def get_brags():
    with _conn() as conn:
        return conn.execute("""
            SELECT b.*, u.name AS user_name, u.color AS user_color,
                   u.profile_photo AS user_photo
            FROM brags b
            JOIN users u ON b.user_id = u.id
            ORDER BY b.created_at DESC
        """).fetchall()


def post_brag(user_id, content, category="other", photo_filename=None):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO brags (user_id, content, category, photo_filename) VALUES (?, ?, ?, ?)",
            (user_id, content, category, photo_filename),
        )
        return cur.lastrowid


def get_brag_by_id(brag_id):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM brags WHERE id = ?", (brag_id,)
        ).fetchone()


def update_brag(brag_id, content, category):
    with _conn() as conn:
        conn.execute(
            "UPDATE brags SET content=?, category=? WHERE id=?",
            (content, category, brag_id),
        )


def delete_brag(brag_id):
    with _conn() as conn:
        conn.execute("DELETE FROM reactions WHERE brag_id = ?", (brag_id,))
        conn.execute("UPDATE wishes SET fulfilled_by_brag_id = NULL WHERE fulfilled_by_brag_id = ?", (brag_id,))
        conn.execute("DELETE FROM brags WHERE id = ?", (brag_id,))


def weekly_stats():
    with _conn() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS brag_count,
                   COUNT(DISTINCT user_id) AS contributor_count
            FROM brags
            WHERE created_at >= datetime('now', '-7 days')
        """).fetchone()
        return dict(row)


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------

def get_reactions_for_brags(brag_ids):
    """Returns {brag_id: [{emoji, user_name, user_id}, ...]}"""
    if not brag_ids:
        return {}
    placeholders = ",".join("?" * len(brag_ids))
    with _conn() as conn:
        rows = conn.execute(f"""
            SELECT r.brag_id, r.emoji, r.user_id, u.name AS user_name
            FROM reactions r
            JOIN users u ON r.user_id = u.id
            WHERE r.brag_id IN ({placeholders})
        """, brag_ids).fetchall()

    result = {bid: [] for bid in brag_ids}
    for row in rows:
        result[row["brag_id"]].append(dict(row))
    return result


def toggle_reaction(brag_id, user_id, emoji):
    """Toggle an emoji reaction. Returns True if added, False if removed."""
    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM reactions WHERE brag_id=? AND user_id=? AND emoji=?",
            (brag_id, user_id, emoji),
        ).fetchone()
        if existing:
            conn.execute(
                "DELETE FROM reactions WHERE brag_id=? AND user_id=? AND emoji=?",
                (brag_id, user_id, emoji),
            )
            return False
        else:
            conn.execute(
                "INSERT INTO reactions (brag_id, user_id, emoji) VALUES (?, ?, ?)",
                (brag_id, user_id, emoji),
            )
            return True


def reaction_summary(brag_id):
    """Returns {emoji: [user_name, ...]} for a single brag."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT r.emoji, u.name AS user_name
            FROM reactions r JOIN users u ON r.user_id = u.id
            WHERE r.brag_id = ?
        """, (brag_id,)).fetchall()
    summary = {}
    for row in rows:
        summary.setdefault(row["emoji"], []).append(row["user_name"])
    return summary


# ---------------------------------------------------------------------------
# Wishes
# ---------------------------------------------------------------------------

def get_wishes():
    with _conn() as conn:
        return conn.execute("""
            SELECT w.*, u.name AS user_name, u.color AS user_color,
                   u.profile_photo AS user_photo, b.content AS fulfilled_content,
                   CAST(julianday('now') - julianday(w.created_at) AS INTEGER) AS days_old
            FROM wishes w
            JOIN users u ON w.user_id = u.id
            LEFT JOIN brags b ON w.fulfilled_by_brag_id = b.id
            ORDER BY w.fulfilled_by_brag_id ASC, w.created_at DESC
        """).fetchall()


def add_wish(user_id, content):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO wishes (user_id, content) VALUES (?, ?)",
            (user_id, content),
        )
        return cur.lastrowid


def get_wish(wish_id):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM wishes WHERE id = ?", (wish_id,)
        ).fetchone()


def claim_wish(wish_id, user_id, category="other"):
    """Mark a wish fulfilled by posting a brag for it. Returns new brag id."""
    with _conn() as conn:
        wish = conn.execute(
            "SELECT * FROM wishes WHERE id = ? AND fulfilled_by_brag_id IS NULL",
            (wish_id,)
        ).fetchone()
        if not wish:
            return None
        brag_content = f"I took care of: {wish['content']}"
        cur = conn.execute(
            "INSERT INTO brags (user_id, content, category) VALUES (?, ?, ?)",
            (user_id, brag_content, category),
        )
        brag_id = cur.lastrowid
        conn.execute(
            "UPDATE wishes SET fulfilled_by_brag_id = ? WHERE id = ?",
            (brag_id, wish_id),
        )
        return brag_id


def delete_wish(wish_id):
    with _conn() as conn:
        conn.execute(
            "DELETE FROM wishes WHERE id = ? AND fulfilled_by_brag_id IS NULL",
            (wish_id,)
        )


# ---------------------------------------------------------------------------
# Points
# ---------------------------------------------------------------------------

DEFAULT_POINTS = {
    "kitchen": 3,
    "home":    4,
    "yard":    5,
    "pets":    3,
    "errands": 2,
    "other":   1,
}


def seed_category_points():
    """Insert default points for any category not yet configured."""
    with _conn() as conn:
        for cat, pts in DEFAULT_POINTS.items():
            conn.execute(
                "INSERT OR IGNORE INTO category_points (category, points) VALUES (?, ?)",
                (cat, pts),
            )


def get_category_points():
    """Returns {category: points} dict."""
    with _conn() as conn:
        rows = conn.execute("SELECT category, points FROM category_points").fetchall()
    return {r["category"]: r["points"] for r in rows}


def set_category_points(category, points):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO category_points (category, points) VALUES (?, ?)"
            " ON CONFLICT(category) DO UPDATE SET points=excluded.points",
            (category, points),
        )


def get_user_points(user_id):
    """Total points earned by a user (sum of points for all their brags)."""
    with _conn() as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(COALESCE(cp.points, 1)), 0) AS total
            FROM brags b
            LEFT JOIN category_points cp ON b.category = cp.category
            WHERE b.user_id = ?
        """, (user_id,)).fetchone()
    return row["total"]


def get_user_points_spent(user_id):
    """Points already spent on approved redemptions."""
    with _conn() as conn:
        row = conn.execute("""
            SELECT COALESCE(SUM(r.points_cost), 0) AS spent
            FROM redemptions red
            JOIN rewards r ON red.reward_id = r.id
            WHERE red.user_id = ? AND red.status = 'approved'
        """, (user_id,)).fetchone()
    return row["spent"]


def get_user_points_balance(user_id):
    return get_user_points(user_id) - get_user_points_spent(user_id)


def get_all_balances():
    """Returns [{user_id, name, color, earned, spent, balance}] for leaderboard."""
    with _conn() as conn:
        earned_rows = conn.execute("""
            SELECT u.id AS user_id, u.name, u.color, u.profile_photo,
                   COALESCE(SUM(COALESCE(cp.points, 1)), 0) AS earned
            FROM users u
            LEFT JOIN brags b ON b.user_id = u.id
            LEFT JOIN category_points cp ON b.category = cp.category
            GROUP BY u.id
        """).fetchall()
        spent_rows = conn.execute("""
            SELECT red.user_id,
                   COALESCE(SUM(r.points_cost), 0) AS spent
            FROM redemptions red
            JOIN rewards r ON red.reward_id = r.id
            WHERE red.status = 'approved'
            GROUP BY red.user_id
        """).fetchall()
    spent_map = {r["user_id"]: r["spent"] for r in spent_rows}
    result = []
    for r in earned_rows:
        earned = r["earned"]
        spent  = spent_map.get(r["user_id"], 0)
        result.append({
            "user_id": r["user_id"],
            "name":    r["name"],
            "color":   r["color"],
            "photo":   r["profile_photo"],
            "earned":  earned,
            "spent":   spent,
            "balance": earned - spent,
        })
    return sorted(result, key=lambda x: x["balance"], reverse=True)


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

def get_active_rewards():
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM rewards WHERE is_active=1 ORDER BY points_cost"
        ).fetchall()


def get_all_rewards():
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM rewards ORDER BY is_active DESC, points_cost"
        ).fetchall()


def create_reward(name, description, points_cost, created_by):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO rewards (name, description, points_cost, created_by)"
            " VALUES (?, ?, ?, ?)",
            (name, description, points_cost, created_by),
        )
        return cur.lastrowid


def toggle_reward_active(reward_id):
    with _conn() as conn:
        conn.execute(
            "UPDATE rewards SET is_active = 1 - is_active WHERE id = ?",
            (reward_id,),
        )


def delete_reward(reward_id):
    with _conn() as conn:
        conn.execute("DELETE FROM rewards WHERE id = ?", (reward_id,))


# ---------------------------------------------------------------------------
# Redemptions
# ---------------------------------------------------------------------------

def get_pending_redemptions():
    with _conn() as conn:
        return conn.execute("""
            SELECT red.*, u.name AS user_name, u.color AS user_color,
                   u.profile_photo AS user_photo, r.name AS reward_name, r.points_cost
            FROM redemptions red
            JOIN users u ON red.user_id = u.id
            JOIN rewards r ON red.reward_id = r.id
            WHERE red.status = 'pending'
            ORDER BY red.requested_at
        """).fetchall()


def get_user_redemptions(user_id):
    with _conn() as conn:
        return conn.execute("""
            SELECT red.*, r.name AS reward_name, r.points_cost
            FROM redemptions red
            JOIN rewards r ON red.reward_id = r.id
            WHERE red.user_id = ?
            ORDER BY red.requested_at DESC
        """, (user_id,)).fetchall()


def request_redemption(user_id, reward_id):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO redemptions (user_id, reward_id) VALUES (?, ?)",
            (user_id, reward_id),
        )
        return cur.lastrowid


def resolve_redemption(redemption_id, status, resolved_by):
    """status: 'approved' or 'denied'"""
    with _conn() as conn:
        conn.execute("""
            UPDATE redemptions
            SET status=?, resolved_at=datetime('now'), resolved_by=?
            WHERE id=?
        """, (status, resolved_by, redemption_id))


# ---------------------------------------------------------------------------
# App settings
# ---------------------------------------------------------------------------

def get_app_setting(key, default=None):
    with _conn() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_app_setting(key, value):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO app_settings (key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def get_denial_cooldown_remaining(user_id, reward_id):
    """Returns hours remaining in cooldown (float), or 0 if no active cooldown."""
    cooldown_hours = int(get_app_setting("denial_cooldown_hours", 24))
    if cooldown_hours == 0:
        return 0
    with _conn() as conn:
        row = conn.execute("""
            SELECT resolved_at FROM redemptions
            WHERE user_id=? AND reward_id=? AND status='denied'
            ORDER BY resolved_at DESC LIMIT 1
        """, (user_id, reward_id)).fetchone()
    if not row or not row["resolved_at"]:
        return 0
    from datetime import datetime
    resolved = datetime.fromisoformat(row["resolved_at"])
    elapsed = (datetime.utcnow() - resolved).total_seconds() / 3600
    remaining = cooldown_hours - elapsed
    return max(0, remaining)


# ---------------------------------------------------------------------------
# Streaks
# ---------------------------------------------------------------------------

def get_user_streak(user_id):
    """Current consecutive-day streak (counts today and/or yesterday as active)."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT date(created_at) AS brag_date
            FROM brags WHERE user_id = ?
            ORDER BY brag_date DESC
        """, (user_id,)).fetchall()
    if not rows:
        return 0
    dates = [date.fromisoformat(r["brag_date"]) for r in rows]
    today = date.today()
    # Streak is active if most recent brag was today or yesterday
    if dates[0] < today - timedelta(days=1):
        return 0
    streak = 1
    for i in range(1, len(dates)):
        if dates[i - 1] - dates[i] == timedelta(days=1):
            streak += 1
        else:
            break
    return streak


def get_user_longest_streak(user_id):
    """All-time longest consecutive-day streak."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT date(created_at) AS brag_date
            FROM brags WHERE user_id = ?
            ORDER BY brag_date DESC
        """, (user_id,)).fetchall()
    if not rows:
        return 0
    dates = [date.fromisoformat(r["brag_date"]) for r in rows]
    longest = current = 1
    for i in range(1, len(dates)):
        if dates[i - 1] - dates[i] == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def get_category_count(user_id, category):
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM brags WHERE user_id=? AND category=?",
            (user_id, category),
        ).fetchone()
    return row["cnt"]


def get_total_brag_count(user_id):
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM brags WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return row["cnt"]


def get_wish_claim_count(user_id):
    """Number of wishes this user has fulfilled."""
    with _conn() as conn:
        row = conn.execute("""
            SELECT COUNT(*) AS cnt FROM brags b
            JOIN wishes w ON w.fulfilled_by_brag_id = b.id
            WHERE b.user_id = ?
        """, (user_id,)).fetchone()
    return row["cnt"]


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------

def award_badge(user_id, badge_slug):
    """Insert badge if not already held. Returns True if newly awarded."""
    with _conn() as conn:
        try:
            conn.execute(
                "INSERT INTO user_badges (user_id, badge_slug) VALUES (?, ?)",
                (user_id, badge_slug),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_user_badges(user_id):
    """Returns list of badge slugs the user holds, ordered by awarded_at."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT badge_slug, awarded_at FROM user_badges WHERE user_id=? ORDER BY awarded_at",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_user_badges():
    """Returns {user_id: [slug, ...]} for all users (for leaderboard display)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT user_id, badge_slug FROM user_badges ORDER BY awarded_at"
        ).fetchall()
    result = {}
    for r in rows:
        result.setdefault(r["user_id"], []).append(r["badge_slug"])
    return result



# ---------------------------------------------------------------------------
# Learn Hub
# ---------------------------------------------------------------------------

DEFAULT_LEARN_SETTINGS = {
    "watch_threshold_pct":    "80",
    "bonus_first_watch":      "50",
    "bonus_repeat_watch":     "10",
    "quiz_pass_threshold":    "2",
    "quiz_pass_multiplier":   "100",
    "quiz_partial_multiplier":"40",
    "quiz_fail_multiplier":   "15",
}


def learn_seed_settings():
    with _conn() as conn:
        for k, v in DEFAULT_LEARN_SETTINGS.items():
            conn.execute("INSERT OR IGNORE INTO learn_settings (key,value) VALUES (?,?)", (k, v))


def learn_get_settings():
    with _conn() as conn:
        rows = conn.execute("SELECT key, value FROM learn_settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def learn_set_setting(key, value):
    with _conn() as conn:
        conn.execute("INSERT INTO learn_settings (key,value) VALUES (?,?) "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def learn_get_categories():
    """Active categories only — used by user-facing pages."""
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM learn_categories WHERE is_active=1 ORDER BY display_order, name"
        ).fetchall()


def learn_get_all_categories():
    """All categories including inactive — used by admin pages."""
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM learn_categories ORDER BY display_order, name"
        ).fetchall()


def learn_create_category(name, emoji, display_order=0, parent_id=None, is_active=1):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO learn_categories (name, emoji, display_order, parent_id, is_active) VALUES (?,?,?,?,?)",
            (name, emoji, display_order, parent_id, is_active),
        )
        return cur.lastrowid


def learn_update_category(cat_id, name, emoji, display_order, parent_id=None, is_active=1):
    with _conn() as conn:
        conn.execute(
            "UPDATE learn_categories SET name=?, emoji=?, display_order=?, parent_id=?, is_active=? WHERE id=?",
            (name, emoji, display_order, parent_id, is_active, cat_id),
        )


def learn_toggle_category(cat_id):
    with _conn() as conn:
        conn.execute(
            "UPDATE learn_categories SET is_active = 1 - is_active WHERE id=?", (cat_id,)
        )


def learn_delete_category(cat_id):
    with _conn() as conn:
        conn.execute("DELETE FROM learn_categories WHERE id=?", (cat_id,))


DEFAULT_BUCKETS = [
    ("Home",   "🏠", 0),
    ("Money",  "💰", 1),
    ("Self",   "🧠", 2),
    ("People", "🤝", 3),
    ("Future", "🎯", 4),
]


def learn_seed_buckets():
    with _conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM learn_categories WHERE parent_id IS NULL").fetchone()[0]
        if count == 0:
            for name, emoji, order in DEFAULT_BUCKETS:
                conn.execute(
                    "INSERT INTO learn_categories (name, emoji, display_order, parent_id, is_active) VALUES (?,?,?,NULL,1)",
                    (name, emoji, order),
                )


def learn_submit_suggestion(user_id, title, description, category_id=None):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO learn_task_suggestions (user_id, title, description, category_id) VALUES (?,?,?,?)",
            (user_id, title, description, category_id),
        )
        return cur.lastrowid


def learn_get_suggestions(status=None):
    with _conn() as conn:
        if status:
            return conn.execute(
                "SELECT s.*, u.name AS user_name FROM learn_task_suggestions s "
                "JOIN users u ON s.user_id=u.id WHERE s.status=? ORDER BY s.created_at DESC",
                (status,),
            ).fetchall()
        return conn.execute(
            "SELECT s.*, u.name AS user_name FROM learn_task_suggestions s "
            "JOIN users u ON s.user_id=u.id ORDER BY s.created_at DESC"
        ).fetchall()


def learn_resolve_suggestion(suggestion_id, status):
    with _conn() as conn:
        conn.execute(
            "UPDATE learn_task_suggestions SET status=? WHERE id=?", (status, suggestion_id)
        )


def learn_get_tasks(category_id=None):
    with _conn() as conn:
        if category_id:
            return conn.execute(
                "SELECT t.*, c.name AS cat_name, c.emoji AS cat_emoji "
                "FROM learn_tasks t JOIN learn_categories c ON t.category_id=c.id "
                "WHERE t.category_id=? AND t.is_active=1 ORDER BY t.title",
                (category_id,),
            ).fetchall()
        return conn.execute(
            "SELECT t.*, c.name AS cat_name, c.emoji AS cat_emoji "
            "FROM learn_tasks t JOIN learn_categories c ON t.category_id=c.id "
            "WHERE t.is_active=1 ORDER BY c.display_order, t.title"
        ).fetchall()


def learn_get_all_tasks():
    with _conn() as conn:
        return conn.execute(
            "SELECT t.*, c.name AS cat_name, c.emoji AS cat_emoji "
            "FROM learn_tasks t JOIN learn_categories c ON t.category_id=c.id "
            "ORDER BY c.display_order, t.title"
        ).fetchall()


def learn_get_task(task_id):
    with _conn() as conn:
        return conn.execute(
            "SELECT t.*, c.name AS cat_name, c.emoji AS cat_emoji "
            "FROM learn_tasks t JOIN learn_categories c ON t.category_id=c.id "
            "WHERE t.id=?", (task_id,)
        ).fetchone()


def learn_create_task(title, description, category_id, youtube_video_id,
                      bonus_first, bonus_repeat, threshold):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO learn_tasks (title, description, category_id, youtube_video_id, "
            "bonus_points_first, bonus_points_repeat, watch_threshold_pct) VALUES (?,?,?,?,?,?,?)",
            (title, description, category_id, youtube_video_id or None,
             bonus_first, bonus_repeat, threshold),
        )
        return cur.lastrowid


def learn_update_task(task_id, title, description, category_id, youtube_video_id,
                      bonus_first, bonus_repeat, threshold, is_active):
    with _conn() as conn:
        conn.execute(
            "UPDATE learn_tasks SET title=?, description=?, category_id=?, "
            "youtube_video_id=?, bonus_points_first=?, bonus_points_repeat=?, "
            "watch_threshold_pct=?, is_active=? WHERE id=?",
            (title, description, category_id, youtube_video_id or None,
             bonus_first, bonus_repeat, threshold, is_active, task_id),
        )


def learn_delete_task(task_id):
    with _conn() as conn:
        conn.execute("DELETE FROM learn_quiz_questions WHERE task_id=?", (task_id,))
        conn.execute("DELETE FROM learn_watch_sessions WHERE task_id=?", (task_id,))
        conn.execute("DELETE FROM learn_completions WHERE task_id=?", (task_id,))
        conn.execute("DELETE FROM learn_tasks WHERE id=?", (task_id,))


def learn_get_quiz_questions(task_id):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM learn_quiz_questions WHERE task_id=? ORDER BY id",
            (task_id,),
        ).fetchall()


def learn_add_question(task_id, question, a, b, c, d, correct):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO learn_quiz_questions (task_id,question,choice_a,choice_b,choice_c,choice_d,correct_choice)"
            " VALUES (?,?,?,?,?,?,?)",
            (task_id, question, a, b, c, d, correct),
        )
        return cur.lastrowid


def learn_delete_question(question_id):
    with _conn() as conn:
        conn.execute("DELETE FROM learn_quiz_questions WHERE id=?", (question_id,))


def learn_get_watch_session(user_id, task_id):
    with _conn() as conn:
        return conn.execute(
            "SELECT * FROM learn_watch_sessions WHERE user_id=? AND task_id=?",
            (user_id, task_id),
        ).fetchone()


def learn_upsert_watch(user_id, task_id, pct):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO learn_watch_sessions (user_id, task_id, pct_watched, updated_at) VALUES (?,?,?,datetime('now')) "
            "ON CONFLICT(user_id, task_id) DO UPDATE SET "
            "pct_watched=MAX(pct_watched, excluded.pct_watched), updated_at=datetime('now')",
            (user_id, task_id, pct),
        )


def learn_is_first_completion(user_id, task_id):
    with _conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM learn_completions WHERE user_id=? AND task_id=?",
            (user_id, task_id),
        ).fetchone()
    return row["cnt"] == 0


def learn_record_completion(user_id, task_id, quiz_score, bonus_awarded, brag_id):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO learn_completions (user_id,task_id,quiz_score,bonus_awarded,brag_id) "
            "VALUES (?,?,?,?,?)",
            (user_id, task_id, quiz_score, bonus_awarded, brag_id),
        )


def learn_get_user_completions(user_id):
    """Returns {task_id: [completion_rows]} for a user."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM learn_completions WHERE user_id=? ORDER BY completed_at DESC",
            (user_id,),
        ).fetchall()
    result = {}
    for r in rows:
        result.setdefault(r["task_id"], []).append(dict(r))
    return result


# ---------------------------------------------------------------------------
# Push subscriptions
# ---------------------------------------------------------------------------

def upsert_push_subscription(user_id, endpoint, p256dh, auth):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET
                user_id=excluded.user_id,
                p256dh=excluded.p256dh,
                auth=excluded.auth
        """, (user_id, endpoint, p256dh, auth))


def delete_push_subscription(endpoint):
    with _conn() as conn:
        conn.execute("DELETE FROM push_subscriptions WHERE endpoint=?", (endpoint,))


def get_all_push_subscriptions():
    with _conn() as conn:
        return conn.execute("SELECT * FROM push_subscriptions").fetchall()


# ---------------------------------------------------------------------------
# Weekly digest
# ---------------------------------------------------------------------------

def get_weekly_digest_data():
    """Collect all data needed to render the weekly email digest."""
    with _conn() as conn:
        week_brags = conn.execute("""
            SELECT b.id, b.content, b.category, b.created_at,
                   u.name AS user_name, u.id AS user_id
            FROM brags b JOIN users u ON b.user_id = u.id
            WHERE b.created_at >= datetime('now', '-7 days')
            ORDER BY b.created_at DESC
        """).fetchall()

        granted = conn.execute("""
            SELECT w.content, u.name AS claimer_name
            FROM wishes w
            JOIN brags b ON w.fulfilled_by_brag_id = b.id
            JOIN users u ON b.user_id = u.id
            WHERE b.created_at >= datetime('now', '-7 days')
        """).fetchall()

    leaderboard = get_all_balances()

    users = get_all_users()
    streaks = []
    for u in users:
        s = get_user_streak(u["id"])
        if s >= 1:
            streaks.append({"name": u["name"], "streak": s})
    streaks.sort(key=lambda x: x["streak"], reverse=True)

    week_brags_list = [dict(b) for b in week_brags]
    contributor_ids = {b["user_id"] for b in week_brags_list}

    return {
        "brag_count":       len(week_brags_list),
        "contributor_count": len(contributor_ids),
        "top_brags":        week_brags_list[:6],
        "leaderboard":      leaderboard,
        "streaks":          streaks,
        "granted":          [dict(g) for g in granted],
    }
