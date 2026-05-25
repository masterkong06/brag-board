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
