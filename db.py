import sqlite3
import os

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


def post_brag(user_id, content, category="other"):
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO brags (user_id, content, category) VALUES (?, ?, ?)",
            (user_id, content, category),
        )
        return cur.lastrowid


def delete_brag(brag_id):
    with _conn() as conn:
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
            SELECT b.user_id, u.name, u.color,
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
