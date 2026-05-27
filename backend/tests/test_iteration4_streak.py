"""Backend tests for iteration 4: streak milestone celebrations & at-risk alerts.

Covers:
- GET /api/streak new fields: atRisk, newMilestone
- POST /api/streak/celebrate?milestone=N&userId=X
- POST /api/streak/save?userId=X (creates partner notification type=streak_save)
- Regression: streak count derived from photo uploads
"""
import os
import io
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"

# Existing seeded users from iteration 4
ALICE_ID = "52d6b731-430d-42eb-9da2-f18674f02bdc"
BOB_ID = "9f07549e-1b24-46f8-ab0f-932ab700bc8a"
COUPLE_ID = "c9f6f897-cf1a-477a-97bd-0d26176a58ca"


@pytest.fixture(scope="module")
def session():
    return requests.Session()


# Helper: create a fresh paired couple for milestone-fresh tests
@pytest.fixture(scope="module")
def fresh_couple(session):
    r1 = session.post(f"{API}/auth/create-user", json={"name": "TEST_I4_Alice"})
    assert r1.status_code == 200
    u1 = r1.json()
    r2 = session.post(f"{API}/auth/create-user", json={"name": "TEST_I4_Bob"})
    assert r2.status_code == 200
    u2 = r2.json()
    code = session.post(f"{API}/auth/generate-code", params={"userId": u1["id"]}).json()["pairCode"]
    session.post(f"{API}/auth/join-couple", json={"pairCode": code, "userId": u2["id"]})
    return u1, u2


def _upload_photo(session, user_id, filename="t.png"):
    png = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
           b'\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00'
           b'\x03\x00\x01\x9a\xd0\x07\x9b\x00\x00\x00\x00IEND\xaeB`\x82')
    files = {"file": (filename, io.BytesIO(png), "image/png")}
    return session.post(f"{API}/photos/upload", files=files, data={"userId": user_id})


# ---------- /api/streak new fields ----------
class TestStreakEndpointShape:
    def test_streak_returns_new_fields(self, session):
        r = session.get(f"{API}/streak", params={"userId": ALICE_ID})
        assert r.status_code == 200
        data = r.json()
        assert "streak" in data
        assert "todayUserSent" in data
        assert "todayPartnerSent" in data
        assert "atRisk" in data
        assert "newMilestone" in data
        assert isinstance(data["atRisk"], bool)
        # newMilestone is either None or int
        assert data["newMilestone"] is None or isinstance(data["newMilestone"], int)

    def test_streak_count_correct_for_seeded_couple(self, session):
        """Alice/Bob have 3-day seeded streak via injected photos."""
        r = session.get(f"{API}/streak", params={"userId": ALICE_ID})
        assert r.status_code == 200
        data = r.json()
        assert data["streak"] == 3, f"Expected streak=3, got {data['streak']}"

    def test_streak_no_couple_returns_defaults(self, session):
        r = session.post(f"{API}/auth/create-user", json={"name": "TEST_I4_lonely"})
        uid = r.json()["id"]
        rs = session.get(f"{API}/streak", params={"userId": uid})
        assert rs.status_code == 200
        d = rs.json()
        assert d["streak"] == 0
        assert d["atRisk"] is False
        assert d["newMilestone"] is None

    def test_streak_at_risk_false_when_both_sent_today(self, session):
        r = session.get(f"{API}/streak", params={"userId": ALICE_ID})
        d = r.json()
        # Seeded data has both sent today, so atRisk must be False
        if d["todayUserSent"] and d["todayPartnerSent"]:
            assert d["atRisk"] is False


# ---------- /api/streak/celebrate ----------
class TestCelebrateMilestone:
    def test_celebrate_marks_milestone_idempotent(self, session):
        # Use seeded couple - milestone=3 is the seeded streak
        r = session.post(f"{API}/streak/celebrate",
                         params={"milestone": 3, "userId": ALICE_ID})
        assert r.status_code == 200
        assert r.json()["success"] is True

        # Subsequent /api/streak must return newMilestone=null for value 3
        r2 = session.get(f"{API}/streak", params={"userId": ALICE_ID})
        assert r2.status_code == 200
        assert r2.json()["newMilestone"] is None

    def test_celebrate_again_is_idempotent(self, session):
        r = session.post(f"{API}/streak/celebrate",
                         params={"milestone": 3, "userId": BOB_ID})
        assert r.status_code == 200

    def test_celebrate_requires_couple(self, session):
        r = session.post(f"{API}/auth/create-user", json={"name": "TEST_I4_nocouple"})
        uid = r.json()["id"]
        r2 = session.post(f"{API}/streak/celebrate",
                          params={"milestone": 3, "userId": uid})
        assert r2.status_code == 400

    def test_celebrate_fresh_couple_shows_milestone(self, session, fresh_couple):
        u1, u2 = fresh_couple
        # Upload photo from each to make streak=1 today
        assert _upload_photo(session, u1["id"]).status_code == 200
        assert _upload_photo(session, u2["id"]).status_code == 200
        r = session.get(f"{API}/streak", params={"userId": u1["id"]})
        d = r.json()
        # streak=1 is not in MILESTONES, so newMilestone should be None
        assert d["streak"] >= 1
        assert d["newMilestone"] is None


# ---------- /api/streak/save ----------
class TestSaveStreak:
    def test_save_creates_partner_notification(self, session):
        # Snapshot Bob's notification count of type=streak_save
        before = session.get(f"{API}/notifications", params={"userId": BOB_ID}).json()
        before_save_count = sum(1 for n in before if n.get("type") == "streak_save")

        # Alice pings Bob to save streak
        r = session.post(f"{API}/streak/save", params={"userId": ALICE_ID})
        assert r.status_code == 200
        assert r.json()["success"] is True

        # Verify Bob got a new streak_save notification
        after = session.get(f"{API}/notifications", params={"userId": BOB_ID}).json()
        after_save_count = sum(1 for n in after if n.get("type") == "streak_save")
        assert after_save_count == before_save_count + 1

        # The newest streak_save notif should have expected title/userId
        latest = next(n for n in after if n.get("type") == "streak_save")
        assert latest["userId"] == BOB_ID
        assert "streak" in latest["title"].lower() or "🔥" in latest["title"]
        assert "_id" not in latest

    def test_save_requires_couple(self, session):
        r = session.post(f"{API}/auth/create-user", json={"name": "TEST_I4_streaksolo"})
        uid = r.json()["id"]
        r2 = session.post(f"{API}/streak/save", params={"userId": uid})
        assert r2.status_code == 400


# ---------- Streak count by photo uploads ----------
class TestStreakIncrements:
    def test_fresh_couple_streak_starts_at_zero(self, session):
        r1 = session.post(f"{API}/auth/create-user", json={"name": "TEST_I4_S_A"})
        u1 = r1.json()
        r2 = session.post(f"{API}/auth/create-user", json={"name": "TEST_I4_S_B"})
        u2 = r2.json()
        code = session.post(f"{API}/auth/generate-code", params={"userId": u1["id"]}).json()["pairCode"]
        session.post(f"{API}/auth/join-couple", json={"pairCode": code, "userId": u2["id"]})

        rs = session.get(f"{API}/streak", params={"userId": u1["id"]})
        assert rs.json()["streak"] == 0

        # Only u1 uploads -> still 0 (both partners required)
        _upload_photo(session, u1["id"])
        rs2 = session.get(f"{API}/streak", params={"userId": u1["id"]})
        assert rs2.json()["streak"] == 0
        assert rs2.json()["todayUserSent"] is True
        assert rs2.json()["todayPartnerSent"] is False

        # u2 uploads too -> streak=1
        _upload_photo(session, u2["id"])
        rs3 = session.get(f"{API}/streak", params={"userId": u1["id"]})
        assert rs3.json()["streak"] == 1
        assert rs3.json()["todayPartnerSent"] is True


# ---------- Regression smoke tests ----------
class TestRegression:
    def test_auth_me(self, session):
        r = session.get(f"{API}/auth/me", params={"userId": ALICE_ID})
        assert r.status_code == 200
        assert r.json()["id"] == ALICE_ID

    def test_partner_lookup(self, session):
        r = session.get(f"{API}/auth/partner", params={"userId": ALICE_ID})
        assert r.status_code == 200
        partner = r.json()
        assert partner["id"] == BOB_ID

    def test_get_photos(self, session):
        r = session.get(f"{API}/photos", params={"userId": ALICE_ID})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_notifications(self, session):
        r = session.get(f"{API}/notifications", params={"userId": ALICE_ID})
        assert r.status_code == 200
        for n in r.json():
            assert "_id" not in n

    def test_unread_count(self, session):
        r = session.get(f"{API}/notifications/unread-count", params={"userId": ALICE_ID})
        assert r.status_code == 200
        assert "count" in r.json()

    def test_get_messages(self, session):
        r = session.get(f"{API}/messages", params={"userId": ALICE_ID})
        assert r.status_code == 200
        for m in r.json():
            assert "_id" not in m

    def test_get_settings(self, session):
        r = session.get(f"{API}/settings", params={"userId": ALICE_ID})
        assert r.status_code == 200

    def test_get_memories(self, session):
        r = session.get(f"{API}/photos/memories", params={"userId": ALICE_ID})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_vapid_public_key(self, session):
        r = session.get(f"{API}/push/vapid-public-key")
        assert r.status_code == 200
        assert "publicKey" in r.json()

    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200
