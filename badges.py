"""
Badge definitions and award logic for the Brag Board.

Each badge has:
  slug        — unique identifier stored in DB
  emoji       — displayed everywhere
  name        — short display name
  desc        — tooltip / description
  check(uid)  — returns True if the user has earned this badge

To add a new badge: add an entry to BADGES and write its check function.
"""

import db

BADGES = [
    {
        "slug":  "first_brag",
        "emoji": "🌱",
        "name":  "First Brag",
        "desc":  "Posted your first brag",
        "check": lambda uid: db.get_total_brag_count(uid) >= 1,
    },
    {
        "slug":  "helper",
        "emoji": "🤝",
        "name":  "Helper",
        "desc":  "Fulfilled someone's wish",
        "check": lambda uid: db.get_wish_claim_count(uid) >= 1,
    },
    {
        "slug":  "streak_3",
        "emoji": "🔥",
        "name":  "On Fire",
        "desc":  "3-day contribution streak",
        "check": lambda uid: db.get_user_longest_streak(uid) >= 3,
    },
    {
        "slug":  "streak_7",
        "emoji": "⚡",
        "name":  "Week Warrior",
        "desc":  "7-day contribution streak",
        "check": lambda uid: db.get_user_longest_streak(uid) >= 7,
    },
    {
        "slug":  "streak_30",
        "emoji": "💎",
        "name":  "Legend",
        "desc":  "30-day contribution streak",
        "check": lambda uid: db.get_user_longest_streak(uid) >= 30,
    },
    {
        "slug":  "pts_50",
        "emoji": "⭐",
        "name":  "Point Collector",
        "desc":  "Earned 50 points",
        "check": lambda uid: db.get_user_points(uid) >= 50,
    },
    {
        "slug":  "pts_200",
        "emoji": "💰",
        "name":  "Centurion",
        "desc":  "Earned 200 points",
        "check": lambda uid: db.get_user_points(uid) >= 200,
    },
    {
        "slug":  "kitchen_5",
        "emoji": "🍽️",
        "name":  "Kitchen Pro",
        "desc":  "5 kitchen brags",
        "check": lambda uid: db.get_category_count(uid, "kitchen") >= 5,
    },
    {
        "slug":  "yard_5",
        "emoji": "🌿",
        "name":  "Green Thumb",
        "desc":  "5 yard brags",
        "check": lambda uid: db.get_category_count(uid, "yard") >= 5,
    },
    {
        "slug":  "home_5",
        "emoji": "🏡",
        "name":  "Home Hero",
        "desc":  "5 home brags",
        "check": lambda uid: db.get_category_count(uid, "home") >= 5,
    },
    {
        "slug":  "pets_5",
        "emoji": "🐾",
        "name":  "Pet Parent",
        "desc":  "5 pet care brags",
        "check": lambda uid: db.get_category_count(uid, "pets") >= 5,
    },
]

# Lookup map for templates
BADGE_MAP = {b["slug"]: b for b in BADGES}


def check_and_award(user_id):
    """
    Check all badge conditions for a user and award any newly earned ones.
    Returns list of newly awarded badge dicts (empty if none).
    """
    newly_awarded = []
    for badge in BADGES:
        try:
            if badge["check"](user_id):
                if db.award_badge(user_id, badge["slug"]):
                    newly_awarded.append(badge)
        except Exception:
            pass  # Never let badge logic break a brag post
    return newly_awarded
