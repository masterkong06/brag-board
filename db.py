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


def user_count():
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


# ---------------------------------------------------------------------------
# Brags
# ---------------------------------------------------------------------------

def get_brags():
    with _conn() as conn:
        return conn.execute("""
            SELECT b.*, u.name AS user_name, u.color AS user_color
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
                   b.content AS fulfilled_content
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
            SELECT u.id AS user_id, u.name, u.color,
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
                   r.name AS reward_name, r.points_cost
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
