"""Backend tests for Memory Link iteration 3 new features:
- /api/streak
- /api/photos/{id}/comment
- /api/messages (POST, GET, mark-read, unread-count)
- /api/settings (GET, PUT)
- /api/photos/memories
"""
import os
import io
import pytest
import requests

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def couple(session):
    # Create two fresh users and pair them
    r1 = session.post(f"{API}/auth/create-user", json={"name": "TEST_I3_Alice"})
    assert r1.status_code == 200, r1.text
    u1 = r1.json()
    r2 = session.post(f"{API}/auth/create-user", json={"name": "TEST_I3_Bob"})
    assert r2.status_code == 200, r2.text
    u2 = r2.json()

    rc = session.post(f"{API}/auth/generate-code", params={"userId": u1["id"]})
    assert rc.status_code == 200
    code = rc.json()["pairCode"]

    rj = session.post(f"{API}/auth/join-couple", json={"pairCode": code, "userId": u2["id"]})
    assert rj.status_code == 200
    return u1, u2


@pytest.fixture(scope="module")
def photo_id(session, couple):
    u1, _ = couple
    png = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
           b'\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00'
           b'\x03\x00\x01\x9a\xd0\x07\x9b\x00\x00\x00\x00IEND\xaeB`\x82')
    files = {"file": ("test.png", io.BytesIO(png), "image/png")}
    r = session.post(f"{API}/photos/upload", files=files, data={"userId": u1["id"], "caption": "TEST i3"})
    assert r.status_code == 200, r.text
    return r.json()["photoId"]


# ---------- Settings ----------
class TestSettings:
    def test_get_default_settings(self, session, couple):
        u1, _ = couple
        r = session.get(f"{API}/settings", params={"userId": u1["id"]})
        assert r.status_code == 200
        data = r.json()
        assert data["dailyReminderEnabled"] is False
        assert data["dailyReminderTime"] == "20:00"
        assert data["inactivityReminderEnabled"] is False
        assert data["inactivityHours"] == 24

    def test_update_and_persist_settings(self, session, couple):
        u1, _ = couple
        payload = {
            "dailyReminderEnabled": True,
            "dailyReminderTime": "09:30",
            "inactivityReminderEnabled": True,
            "inactivityHours": 48,
        }
        r = session.put(f"{API}/settings", params={"userId": u1["id"]}, json=payload)
        assert r.status_code == 200
        assert r.json()["success"] is True

        # GET to verify persistence
        r2 = session.get(f"{API}/settings", params={"userId": u1["id"]})
        assert r2.status_code == 200
        d = r2.json()
        assert d["dailyReminderEnabled"] is True
        assert d["dailyReminderTime"] == "09:30"
        assert d["inactivityReminderEnabled"] is True
        assert d["inactivityHours"] == 48

    def test_update_settings_upsert_second_user(self, session, couple):
        _, u2 = couple
        payload = {
            "dailyReminderEnabled": True,
            "dailyReminderTime": "07:00",
            "inactivityReminderEnabled": False,
            "inactivityHours": 24,
        }
        r = session.put(f"{API}/settings", params={"userId": u2["id"]}, json=payload)
        assert r.status_code == 200
        # User 1's settings should be unchanged from prior test
        r1 = session.get(f"{API}/settings", params={"userId": couple[0]["id"]})
        assert r1.json()["dailyReminderTime"] == "09:30"


# ---------- Comments ----------
class TestComments:
    def test_add_comment_by_partner(self, session, couple, photo_id):
        _, u2 = couple
        r = session.post(
            f"{API}/photos/{photo_id}/comment",
            params={"userId": u2["id"]},
            json={"text": "TEST_so cute!"}
        )
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["text"] == "TEST_so cute!"
        assert c["userId"] == u2["id"]
        assert "id" in c
        # _id should NOT be in response (mongo ObjectId)
        assert "_id" not in c

    def test_comment_embedded_in_photo_list(self, session, couple, photo_id):
        u1, _ = couple
        r = session.get(f"{API}/photos", params={"userId": u1["id"]})
        assert r.status_code == 200
        photos = r.json()
        target = next((p for p in photos if p["id"] == photo_id), None)
        assert target is not None
        assert "comments" in target
        assert len(target["comments"]) >= 1
        assert any(c["text"] == "TEST_so cute!" for c in target["comments"])

    def test_comment_creates_notification_for_uploader(self, session, couple, photo_id):
        u1, _ = couple
        # u1 is uploader; comment was made by u2 -> notification for u1
        r = session.get(f"{API}/notifications", params={"userId": u1["id"]})
        assert r.status_code == 200
        notifs = r.json()
        assert any(n.get("type") == "comment" and n.get("payload", {}).get("photoId") == photo_id for n in notifs)

    def test_comment_invalid_photo(self, session, couple):
        u1, _ = couple
        r = session.post(
            f"{API}/photos/does-not-exist/comment",
            params={"userId": u1["id"]},
            json={"text": "x"}
        )
        assert r.status_code == 404


# ---------- Messages ----------
class TestMessages:
    def test_send_message(self, session, couple):
        u1, _ = couple
        r = session.post(f"{API}/messages", params={"userId": u1["id"]}, json={"text": "TEST_hi partner"})
        assert r.status_code == 200, r.text
        msg = r.json()
        assert msg["text"] == "TEST_hi partner"
        assert msg["senderId"] == u1["id"]
        assert "id" in msg
        assert "_id" not in msg  # Mongo ObjectId should be stripped

    def test_get_messages(self, session, couple):
        u1, _ = couple
        r = session.get(f"{API}/messages", params={"userId": u1["id"]})
        assert r.status_code == 200
        messages = r.json()
        assert isinstance(messages, list)
        assert len(messages) >= 1
        assert any(m["text"] == "TEST_hi partner" for m in messages)
        # Ensure none have _id
        for m in messages:
            assert "_id" not in m

    def test_unread_count_for_partner(self, session, couple):
        _, u2 = couple
        r = session.get(f"{API}/messages/unread-count", params={"userId": u2["id"]})
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_mark_read(self, session, couple):
        _, u2 = couple
        r = session.post(f"{API}/messages/mark-read", params={"userId": u2["id"]})
        assert r.status_code == 200
        assert r.json()["success"] is True
        # Verify count is now 0
        r2 = session.get(f"{API}/messages/unread-count", params={"userId": u2["id"]})
        assert r2.json()["count"] == 0

    def test_message_creates_notification(self, session, couple):
        _, u2 = couple
        r = session.get(f"{API}/notifications", params={"userId": u2["id"]})
        assert r.status_code == 200
        notifs = r.json()
        assert any(n.get("type") == "message" for n in notifs)

    def test_send_message_no_couple(self, session):
        r = session.post(f"{API}/auth/create-user", json={"name": "TEST_lonely"})
        uid = r.json()["id"]
        r2 = session.post(f"{API}/messages", params={"userId": uid}, json={"text": "hi"})
        assert r2.status_code == 400


# ---------- Streak ----------
class TestStreak:
    def test_streak_after_both_today(self, session, couple, photo_id):
        u1, u2 = couple
        # u1 already uploaded photo_id; have u2 upload too so today both sent
        png = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
               b'\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00'
               b'\x03\x00\x01\x9a\xd0\x07\x9b\x00\x00\x00\x00IEND\xaeB`\x82')
        files = {"file": ("test2.png", io.BytesIO(png), "image/png")}
        r = session.post(f"{API}/photos/upload", files=files, data={"userId": u2["id"]})
        assert r.status_code == 200

        rs = session.get(f"{API}/streak", params={"userId": u1["id"]})
        assert rs.status_code == 200
        d = rs.json()
        assert d["todayUserSent"] is True
        assert d["todayPartnerSent"] is True
        assert d["streak"] >= 1

    def test_streak_no_couple(self, session):
        r = session.post(f"{API}/auth/create-user", json={"name": "TEST_streaksolo"})
        uid = r.json()["id"]
        rs = session.get(f"{API}/streak", params={"userId": uid})
        assert rs.status_code == 200
        assert rs.json()["streak"] == 0
        assert rs.json()["todayUserSent"] is False


# ---------- Memories ----------
class TestMemories:
    def test_memories_empty_for_new_couple(self, session, couple):
        u1, _ = couple
        r = session.get(f"{API}/photos/memories", params={"userId": u1["id"]})
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        # Likely empty since photos uploaded today (this year)
        for p in r.json():
            assert "_id" not in p

    def test_memories_no_couple(self, session):
        r = session.post(f"{API}/auth/create-user", json={"name": "TEST_memsolo"})
        uid = r.json()["id"]
        r2 = session.get(f"{API}/photos/memories", params={"userId": uid})
        assert r2.status_code == 200
        assert r2.json() == []
