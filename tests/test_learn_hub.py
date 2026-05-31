"""
Learn Hub test suite.
Run from the repo root:  python -m pytest tests/test_learn_hub.py -v
"""
import os
import sys
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("SMTP_USER", "x")
os.environ.setdefault("SMTP_PASSWORD", "x")
os.environ.setdefault("SITE_URL", "http://localhost")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import db
import app as application

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Each test gets its own isolated SQLite database."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()
    db.seed_category_points()
    db.learn_seed_settings()
    yield db_path


@pytest.fixture()
def client():
    application.app.config["TESTING"] = True
    with application.app.test_client() as c:
        yield c


@pytest.fixture()
def admin_user():
    db.create_user("Admin", "admin", "hash", color="#4361ee", is_admin=1)
    return db.get_user_by_username("admin")


@pytest.fixture()
def regular_user():
    db.create_user("Alice", "alice", "hash", color="#f72585", is_admin=0)
    return db.get_user_by_username("alice")


def _login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"]    = user["id"]
        sess["user_name"]  = user["name"]
        sess["username"]   = user["username"]
        sess["user_color"] = user["color"]
        sess["is_admin"]   = bool(user["is_admin"])


# ---------------------------------------------------------------------------
# DB layer — categories
# ---------------------------------------------------------------------------

class TestLearnCategories:
    def test_create_and_get(self):
        cat_id = db.learn_create_category("Kitchen", "🍽️", display_order=1)
        cats = db.learn_get_categories()
        assert len(cats) == 1
        assert cats[0]["name"] == "Kitchen"
        assert cats[0]["emoji"] == "🍽️"

    def test_update(self):
        cat_id = db.learn_create_category("Old", "❓")
        db.learn_update_category(cat_id, "New", "✅", display_order=5)
        cats = db.learn_get_categories()
        assert cats[0]["name"] == "New"
        assert cats[0]["display_order"] == 5

    def test_delete(self):
        cat_id = db.learn_create_category("Temp", "🗑️")
        db.learn_delete_category(cat_id)
        assert db.learn_get_categories() == []

    def test_display_order_sorting(self):
        db.learn_create_category("B", "🅱️", display_order=2)
        db.learn_create_category("A", "🅰️", display_order=1)
        cats = db.learn_get_categories()
        assert cats[0]["name"] == "A"
        assert cats[1]["name"] == "B"


# ---------------------------------------------------------------------------
# DB layer — tasks
# ---------------------------------------------------------------------------

class TestLearnTasks:
    def setup_method(self):
        self.cat_id = db.learn_create_category("Kitchen", "🍽️")

    def test_create_and_get(self):
        task_id = db.learn_create_task(
            "Clean the stove", "Scrub burners", self.cat_id,
            "dQw4w9WgXcQ", bonus_first=50, bonus_repeat=10, threshold=80
        )
        task = db.learn_get_task(task_id)
        assert task["title"] == "Clean the stove"
        assert task["youtube_video_id"] == "dQw4w9WgXcQ"
        assert task["bonus_points_first"] == 50
        assert task["cat_name"] == "Kitchen"

    def test_get_tasks_by_category(self):
        cat2 = db.learn_create_category("Yard", "🌿")
        db.learn_create_task("Task A", "", self.cat_id, None, 50, 10, 80)
        db.learn_create_task("Task B", "", cat2, None, 50, 10, 80)
        assert len(db.learn_get_tasks(self.cat_id)) == 1
        assert len(db.learn_get_tasks(cat2)) == 1
        assert len(db.learn_get_tasks()) == 2

    def test_inactive_tasks_hidden(self):
        task_id = db.learn_create_task("Task", "", self.cat_id, None, 50, 10, 80)
        db.learn_update_task(task_id, "Task", "", self.cat_id, None, 50, 10, 80, is_active=0)
        assert db.learn_get_tasks() == []
        assert len(db.learn_get_all_tasks()) == 1

    def test_delete_cascades(self):
        task_id = db.learn_create_task("Task", "", self.cat_id, None, 50, 10, 80)
        db.learn_add_question(task_id, "Q?", "A", "B", "C", "D", "a")
        db.learn_delete_task(task_id)
        assert db.learn_get_task(task_id) is None
        assert db.learn_get_quiz_questions(task_id) == []


# ---------------------------------------------------------------------------
# DB layer — quiz questions
# ---------------------------------------------------------------------------

class TestLearnQuiz:
    def setup_method(self):
        cat_id = db.learn_create_category("Kitchen", "🍽️")
        self.task_id = db.learn_create_task("Task", "", cat_id, "vid123", 50, 10, 80)

    def test_add_and_get_questions(self):
        db.learn_add_question(self.task_id, "What?", "A", "B", "C", "D", "b")
        db.learn_add_question(self.task_id, "Why?", "W", "X", "Y", "Z", "c")
        qs = db.learn_get_quiz_questions(self.task_id)
        assert len(qs) == 2
        assert qs[0]["correct_choice"] == "b"

    def test_delete_question(self):
        q_id = db.learn_add_question(self.task_id, "Q?", "A", "B", "C", "D", "a")
        db.learn_delete_question(q_id)
        assert db.learn_get_quiz_questions(self.task_id) == []


# ---------------------------------------------------------------------------
# DB layer — watch sessions & completions
# ---------------------------------------------------------------------------

class TestLearnProgress:
    def setup_method(self):
        db.create_user("User", "user", "hash", color="#fff", is_admin=0)
        self.user = db.get_user_by_username("user")
        cat_id = db.learn_create_category("Kitchen", "🍽️")
        self.task_id = db.learn_create_task("Task", "", cat_id, "vid", 50, 10, 80)

    def test_watch_upsert_increases_pct(self):
        db.learn_upsert_watch(self.user["id"], self.task_id, 40)
        db.learn_upsert_watch(self.user["id"], self.task_id, 70)
        session = db.learn_get_watch_session(self.user["id"], self.task_id)
        assert session["pct_watched"] == 70

    def test_watch_never_decreases(self):
        db.learn_upsert_watch(self.user["id"], self.task_id, 90)
        db.learn_upsert_watch(self.user["id"], self.task_id, 30)
        session = db.learn_get_watch_session(self.user["id"], self.task_id)
        assert session["pct_watched"] == 90

    def test_is_first_completion(self):
        assert db.learn_is_first_completion(self.user["id"], self.task_id) is True
        db.learn_record_completion(self.user["id"], self.task_id, 3, 50, None)
        assert db.learn_is_first_completion(self.user["id"], self.task_id) is False

    def test_get_user_completions(self):
        db.learn_record_completion(self.user["id"], self.task_id, 2, 20, None)
        db.learn_record_completion(self.user["id"], self.task_id, 1, 10, None)
        completions = db.learn_get_user_completions(self.user["id"])
        assert len(completions[self.task_id]) == 2


# ---------------------------------------------------------------------------
# DB layer — settings
# ---------------------------------------------------------------------------

class TestLearnSettings:
    def test_default_settings_seeded(self):
        s = db.learn_get_settings()
        assert s["watch_threshold_pct"] == "80"
        assert s["bonus_first_watch"] == "50"
        assert s["quiz_pass_multiplier"] == "100"

    def test_update_setting(self):
        db.learn_set_setting("watch_threshold_pct", "60")
        assert db.learn_get_settings()["watch_threshold_pct"] == "60"


# ---------------------------------------------------------------------------
# Routes — /learn (browse)
# ---------------------------------------------------------------------------

class TestLearnRoutes:
    def test_learn_redirects_when_not_logged_in(self, client):
        r = client.get("/learn")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_learn_page_loads(self, client, regular_user):
        _login(client, regular_user)
        r = client.get("/learn")
        assert r.status_code == 200
        assert b"Learn Hub" in r.data

    def test_learn_shows_categories_and_tasks(self, client, regular_user):
        cat_id = db.learn_create_category("Kitchen", "🍽️")
        db.learn_create_task("Clean stove", "", cat_id, None, 50, 10, 80)
        _login(client, regular_user)
        r = client.get("/learn")
        assert b"Kitchen" in r.data
        assert b"Clean stove" in r.data

    def test_learn_filter_by_category(self, client, regular_user):
        cat1 = db.learn_create_category("Kitchen", "🍽️")
        cat2 = db.learn_create_category("Yard", "🌿")
        db.learn_create_task("Stove", "", cat1, None, 50, 10, 80)
        db.learn_create_task("Mow", "", cat2, None, 50, 10, 80)
        _login(client, regular_user)
        r = client.get(f"/learn?cat={cat1}")
        assert b"Stove" in r.data
        assert b"Mow" not in r.data

    def test_learn_task_detail(self, client, regular_user):
        cat_id = db.learn_create_category("Kitchen", "🍽️")
        task_id = db.learn_create_task("Clean stove", "Scrub it", cat_id, "vid123", 50, 10, 80)
        _login(client, regular_user)
        r = client.get(f"/learn/{task_id}")
        assert r.status_code == 200
        assert b"Clean stove" in r.data
        assert b"Scrub it" in r.data


# ---------------------------------------------------------------------------
# Routes — watch progress
# ---------------------------------------------------------------------------

class TestWatchRoute:
    def test_watch_records_progress(self, client, regular_user):
        cat_id = db.learn_create_category("Kitchen", "🍽️")
        task_id = db.learn_create_task("Task", "", cat_id, "vid", 50, 10, 80)
        _login(client, regular_user)
        r = client.post(f"/learn/{task_id}/watch",
                        json={"pct": 50},
                        content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert data["unlocked"] is False

    def test_watch_reports_unlocked_at_threshold(self, client, regular_user):
        cat_id = db.learn_create_category("Kitchen", "🍽️")
        task_id = db.learn_create_task("Task", "", cat_id, "vid", 50, 10, 80)
        _login(client, regular_user)
        r = client.post(f"/learn/{task_id}/watch",
                        json={"pct": 80},
                        content_type="application/json")
        assert r.get_json()["unlocked"] is True


# ---------------------------------------------------------------------------
# Routes — completion & bonus points
# ---------------------------------------------------------------------------

class TestCompleteRoute:
    def setup_method(self):
        db.create_user("Admin", "admin", "hash", color="#fff", is_admin=1)
        self.admin = db.get_user_by_username("admin")
        cat_id = db.learn_create_category("kitchen", "🍽️")
        self.task_id = db.learn_create_task("Clean stove", "", cat_id, "vid", 50, 10, 80)
        db.learn_add_question(self.task_id, "Q1?", "Right", "Wrong", "Wrong", "Wrong", "a")
        db.learn_add_question(self.task_id, "Q2?", "Wrong", "Right", "Wrong", "Wrong", "b")
        db.learn_add_question(self.task_id, "Q3?", "Wrong", "Wrong", "Right", "Wrong", "c")

    def test_complete_requires_brag_content(self, client):
        _login(client, self.admin)
        db.learn_upsert_watch(self.admin["id"], self.task_id, 80)
        r = client.post(f"/learn/{self.task_id}/complete",
                        data={"brag_content": ""})
        assert r.status_code == 302
        # Should redirect back to the task page, not to the feed
        assert f"/learn/{self.task_id}" in r.headers["Location"]

    def test_complete_full_pass_awards_full_bonus(self, client):
        _login(client, self.admin)
        db.learn_upsert_watch(self.admin["id"], self.task_id, 80)
        qs = db.learn_get_quiz_questions(self.task_id)
        form = {
            "brag_content": "I cleaned the stove!",
            f"q{qs[0]['id']}": "a",
            f"q{qs[1]['id']}": "b",
            f"q{qs[2]['id']}": "c",
        }
        r = client.post(f"/learn/{self.task_id}/complete", data=form)
        assert r.status_code == 302
        completions = db.learn_get_user_completions(self.admin["id"])
        assert self.task_id in completions
        c = completions[self.task_id][0]
        assert c["quiz_score"] == 3
        assert c["bonus_awarded"] == 50  # 100% of 50

    def test_complete_partial_pass_awards_partial_bonus(self, client):
        _login(client, self.admin)
        db.learn_upsert_watch(self.admin["id"], self.task_id, 80)
        qs = db.learn_get_quiz_questions(self.task_id)
        form = {
            "brag_content": "Did it!",
            f"q{qs[0]['id']}": "a",   # correct
            f"q{qs[1]['id']}": "a",   # wrong
            f"q{qs[2]['id']}": "a",   # wrong
        }
        client.post(f"/learn/{self.task_id}/complete", data=form)
        c = db.learn_get_user_completions(self.admin["id"])[self.task_id][0]
        assert c["quiz_score"] == 1
        # score=1 == pass_threshold-1 (2-1=1) → partial multiplier 40%
        assert c["bonus_awarded"] == round(50 * 40 / 100)

    def test_repeat_completion_awards_repeat_bonus(self, client):
        _login(client, self.admin)
        db.learn_record_completion(self.admin["id"], self.task_id, 3, 50, None)
        r = client.post(f"/learn/{self.task_id}/complete",
                        data={"brag_content": "Did it again!"})
        assert r.status_code == 302
        completions = db.learn_get_user_completions(self.admin["id"])[self.task_id]
        repeat = completions[0]
        assert repeat["bonus_awarded"] == 10  # repeat bonus


# ---------------------------------------------------------------------------
# Routes — admin
# ---------------------------------------------------------------------------

class TestAdminRoutes:
    def test_admin_page_requires_admin(self, client, regular_user):
        _login(client, regular_user)
        r = client.get("/learn/admin")
        assert r.status_code == 302  # redirected away

    def test_admin_page_loads_for_admin(self, client, admin_user):
        _login(client, admin_user)
        r = client.get("/learn/admin")
        assert r.status_code == 200
        assert b"Learn Hub Admin" in r.data

    def test_admin_create_category(self, client, admin_user):
        _login(client, admin_user)
        client.post("/learn/admin/category/new",
                    data={"name": "Pets", "emoji": "🐾", "display_order": "2"})
        cats = db.learn_get_categories()
        assert any(c["name"] == "Pets" for c in cats)

    def test_admin_delete_category(self, client, admin_user):
        cat_id = db.learn_create_category("Temp", "🗑️")
        _login(client, admin_user)
        client.post(f"/learn/admin/category/{cat_id}/delete")
        assert db.learn_get_categories() == []

    def test_admin_create_task(self, client, admin_user):
        cat_id = db.learn_create_category("Kitchen", "🍽️")
        _login(client, admin_user)
        client.post("/learn/admin/task/new", data={
            "title": "Wash dishes",
            "description": "Scrub them good",
            "category_id": str(cat_id),
            "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
            "bonus_first": "60",
            "bonus_repeat": "15",
            "threshold": "75",
        })
        tasks = db.learn_get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Wash dishes"
        assert tasks[0]["youtube_video_id"] == "dQw4w9WgXcQ"

    def test_admin_delete_task(self, client, admin_user):
        cat_id = db.learn_create_category("Kitchen", "🍽️")
        task_id = db.learn_create_task("Task", "", cat_id, None, 50, 10, 80)
        _login(client, admin_user)
        client.post(f"/learn/admin/task/{task_id}/delete")
        assert db.learn_get_task(task_id) is None

    def test_admin_save_settings(self, client, admin_user):
        _login(client, admin_user)
        client.post("/learn/admin/settings", data={
            "watch_threshold_pct":     "70",
            "bonus_first_watch":       "100",
            "bonus_repeat_watch":      "20",
            "quiz_pass_threshold":     "2",
            "quiz_pass_multiplier":    "90",
            "quiz_partial_multiplier": "50",
            "quiz_fail_multiplier":    "10",
        })
        s = db.learn_get_settings()
        assert s["watch_threshold_pct"] == "70"
        assert s["bonus_first_watch"] == "100"


# ---------------------------------------------------------------------------
# YouTube ID extraction helper
# ---------------------------------------------------------------------------

class TestYouTubeExtractor:
    def test_full_url(self):
        from app import _extract_youtube_id
        assert _extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        from app import _extract_youtube_id
        assert _extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        from app import _extract_youtube_id
        assert _extract_youtube_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_bare_id(self):
        from app import _extract_youtube_id
        assert _extract_youtube_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_empty_returns_none(self):
        from app import _extract_youtube_id
        assert _extract_youtube_id("") is None
        assert _extract_youtube_id(None) is None
