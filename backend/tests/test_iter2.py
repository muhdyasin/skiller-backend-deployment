"""Iteration 2 backend tests for Skiller new features.
Covers: upload + file fetch, notifications, AI recommend, ads, dashboard, courses CRUD,
leaderboard, /users/me/xp, XP rules, badges, daily-login streak idempotency, /users/{username} level+badges.
"""
import io
import os
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://skiller-connect.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

# ---------- helpers ----------
def login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


def H(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def maya():
    t, u = login("maya@skiller.app", "Demo@123")
    return {"t": t, "u": u}


@pytest.fixture(scope="module")
def arjun():
    t, u = login("arjun@skiller.app", "Demo@123")
    return {"t": t, "u": u}


@pytest.fixture(scope="module")
def neha():
    t, u = login("neha@skiller.app", "Demo@123")
    return {"t": t, "u": u}


@pytest.fixture(scope="module")
def freshuser():
    """Create a fresh TEST_ user for XP/badge testing without polluting demo data."""
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"TEST_{suffix}@skiller.app",
        "password": "Test@1234",
        "name": f"Test {suffix}",
        "username": f"test_{suffix}",
    }
    r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return {"t": r.json()["token"], "u": r.json()["user"], "email": payload["email"]}


# ---------- upload + files ----------
PNG_1x1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4"
    "890000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
)


class TestUploadAndFiles:
    def test_upload_requires_auth(self):
        r = requests.post(f"{API}/upload", files={"file": ("a.png", PNG_1x1, "image/png")}, timeout=30)
        assert r.status_code == 401

    def test_upload_returns_url_and_path(self, maya):
        files = {"file": ("test.png", PNG_1x1, "image/png")}
        r = requests.post(f"{API}/upload", files=files, headers=H(maya["t"]), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "url" in data and data["url"].startswith("/api/files/")
        assert "path" in data and data["path"]
        assert data["content_type"] == "image/png"
        assert data["size"] > 0
        # store for next test
        TestUploadAndFiles._path = data["path"]

    def test_get_file_streams_bytes(self):
        path = TestUploadAndFiles._path
        r = requests.get(f"{API}/files/{path}", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


# ---------- notifications ----------
class TestNotifications:
    def test_like_creates_notification_for_target_not_actor(self, maya, arjun):
        # find a post by arjun
        feed = requests.get(f"{API}/posts/feed").json()
        arj = next(p for p in feed if p["author"]["username"] == "arjun")
        # maya likes (toggle - ensure it ends in liked state)
        r1 = requests.post(f"{API}/posts/{arj['id']}/like", headers=H(maya["t"]), timeout=30)
        assert r1.status_code == 200
        if not r1.json()["liked"]:
            requests.post(f"{API}/posts/{arj['id']}/like", headers=H(maya["t"]), timeout=30)
        # arjun should have a like-notif from maya
        notifs = requests.get(f"{API}/notifications", headers=H(arjun["t"]), timeout=30).json()
        assert any(n["kind"] == "like" and n.get("actor", {}).get("username") == "maya" for n in notifs)
        # maya should NOT have a like-notif from herself
        my_notifs = requests.get(f"{API}/notifications", headers=H(maya["t"]), timeout=30).json()
        assert not any(n["kind"] == "like" and n.get("actor", {}).get("username") == "maya" for n in my_notifs)

    def test_unread_count_and_read_all(self, arjun):
        r = requests.get(f"{API}/notifications/unread-count", headers=H(arjun["t"]), timeout=30)
        assert r.status_code == 200
        assert "count" in r.json()
        rr = requests.post(f"{API}/notifications/read-all", headers=H(arjun["t"]), timeout=30)
        assert rr.status_code == 200
        c = requests.get(f"{API}/notifications/unread-count", headers=H(arjun["t"]), timeout=30).json()["count"]
        assert c == 0

    def test_mark_one_read(self, maya, neha):
        # neha comments on a maya post -> maya gets notif
        feed = requests.get(f"{API}/posts/feed").json()
        m = next(p for p in feed if p["author"]["username"] == "maya")
        r = requests.post(f"{API}/posts/{m['id']}/comments", json={"text": "TEST_iter2"}, headers=H(neha["t"]), timeout=30)
        assert r.status_code == 200
        notifs = requests.get(f"{API}/notifications", headers=H(maya["t"]), timeout=30).json()
        target = next(n for n in notifs if n["kind"] == "comment" and not n["read"])
        rr = requests.post(f"{API}/notifications/{target['id']}/read", headers=H(maya["t"]), timeout=30)
        assert rr.status_code == 200

    def test_follow_creates_notification(self, freshuser, maya):
        r = requests.post(f"{API}/users/{maya['u']['id']}/follow", headers=H(freshuser["t"]), timeout=30)
        assert r.status_code == 200
        notifs = requests.get(f"{API}/notifications", headers=H(maya["t"]), timeout=30).json()
        assert any(n["kind"] == "follow" and n.get("actor", {}).get("username") == freshuser["u"]["username"] for n in notifs)


# ---------- ai recommend ----------
class TestAIRecommend:
    def test_ai_recommend_shape(self, maya):
        r = requests.get(f"{API}/ai/recommend", headers=H(maya["t"]), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("courses", "gigs", "creators"):
            assert k in data
            assert isinstance(data[k], list)
            assert len(data[k]) <= 3
            for item in data[k]:
                assert "why" in item and isinstance(item["why"], str)


# ---------- ads ----------
class TestAds:
    def test_full_ad_lifecycle(self, maya):
        payload = {
            "title": "TEST_ad", "caption": "test", "media": "https://x/y.jpg",
            "cta_label": "Go", "cta_url": "https://example.com",
            "daily_budget": 100, "duration_days": 1,
        }
        r = requests.post(f"{API}/ads", json=payload, headers=H(maya["t"]), timeout=30)
        assert r.status_code == 200, r.text
        ad = r.json()
        assert ad["status"] == "active"
        ad_id = ad["id"]
        # mine
        mine = requests.get(f"{API}/ads/mine", headers=H(maya["t"]), timeout=30).json()
        assert any(a["id"] == ad_id for a in mine)
        # active impressions: call twice, verify increment
        a1 = requests.get(f"{API}/ads/active", timeout=30).json()
        my_ad = next((a for a in a1 if a["id"] == ad_id), None)
        if my_ad:
            imp1 = my_ad["impressions"]
            requests.get(f"{API}/ads/active", timeout=30)
            mine2 = requests.get(f"{API}/ads/mine", headers=H(maya["t"]), timeout=30).json()
            same = next(a for a in mine2 if a["id"] == ad_id)
            assert same["impressions"] >= imp1 + 1
        # click increments clicks+spend
        before = next(a for a in requests.get(f"{API}/ads/mine", headers=H(maya["t"])).json() if a["id"] == ad_id)
        requests.post(f"{API}/ads/{ad_id}/click", timeout=30)
        after = next(a for a in requests.get(f"{API}/ads/mine", headers=H(maya["t"])).json() if a["id"] == ad_id)
        assert after["clicks"] == before["clicks"] + 1
        assert after["spend"] == before["spend"] + 8
        # pause
        rp = requests.patch(f"{API}/ads/{ad_id}/status", json={"status": "paused"}, headers=H(maya["t"]), timeout=30)
        assert rp.status_code == 200
        paused = next(a for a in requests.get(f"{API}/ads/mine", headers=H(maya["t"])).json() if a["id"] == ad_id)
        assert paused["status"] == "paused"
        # delete
        rd = requests.delete(f"{API}/ads/{ad_id}", headers=H(maya["t"]), timeout=30)
        assert rd.status_code == 200
        gone = [a for a in requests.get(f"{API}/ads/mine", headers=H(maya["t"])).json() if a["id"] == ad_id]
        assert gone == []


# ---------- dashboard ----------
class TestDashboard:
    def test_stats_shape(self, maya):
        r = requests.get(f"{API}/dashboard/stats", headers=H(maya["t"]), timeout=30)
        assert r.status_code == 200
        s = r.json()
        for k in ("posts","likes","comments","followers","courses","enrollments",
                  "active_ads","ad_impressions","ad_clicks","ad_spend","ad_ctr","xp","level"):
            assert k in s, f"missing {k}"
        assert "level" in s["level"] and "name" in s["level"]


# ---------- courses CRUD ----------
class TestCourses:
    def test_create_update_delete_owner_only(self, maya, arjun):
        # maya creates
        r = requests.post(f"{API}/courses", json={
            "title": "TEST_course", "description": "x", "price": 0, "lessons": 1,
            "thumbnail": "", "category": "Test"
        }, headers=H(maya["t"]), timeout=30)
        assert r.status_code == 200
        cid = r.json()["id"]
        assert r.json()["owner_id"] == maya["u"]["id"]
        # appears in /dashboard/courses
        mine = requests.get(f"{API}/dashboard/courses", headers=H(maya["t"]), timeout=30).json()
        assert any(c["id"] == cid for c in mine)
        # arjun cannot patch
        bad = requests.patch(f"{API}/courses/{cid}", json={"title": "hax"}, headers=H(arjun["t"]), timeout=30)
        assert bad.status_code == 403
        # arjun cannot delete
        bad2 = requests.delete(f"{API}/courses/{cid}", headers=H(arjun["t"]), timeout=30)
        assert bad2.status_code == 403
        # owner patches
        ok = requests.patch(f"{API}/courses/{cid}", json={"title": "TEST_course2"}, headers=H(maya["t"]), timeout=30)
        assert ok.status_code == 200
        assert ok.json()["title"] == "TEST_course2"
        # owner deletes
        rd = requests.delete(f"{API}/courses/{cid}", headers=H(maya["t"]), timeout=30)
        assert rd.status_code == 200

    def test_enroll_idempotent_and_xp(self, freshuser):
        courses = requests.get(f"{API}/courses", timeout=30).json()
        cid = courses[0]["id"]
        before = requests.get(f"{API}/users/me/xp", headers=H(freshuser["t"])).json()["xp"]
        r1 = requests.post(f"{API}/courses/{cid}/enroll", headers=H(freshuser["t"]), timeout=30)
        assert r1.status_code == 200
        mid = requests.get(f"{API}/users/me/xp", headers=H(freshuser["t"])).json()["xp"]
        assert mid >= before + 10
        # second call -> already
        r2 = requests.post(f"{API}/courses/{cid}/enroll", headers=H(freshuser["t"]), timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("already") is True
        after = requests.get(f"{API}/users/me/xp", headers=H(freshuser["t"])).json()["xp"]
        assert after == mid  # no extra XP


# ---------- leaderboard, /users/me/xp, /users/{username} ----------
class TestXPandLeaderboard:
    def test_leaderboard_sorted_desc(self):
        r = requests.get(f"{API}/leaderboard", timeout=30)
        assert r.status_code == 200
        users = r.json()
        assert len(users) >= 1
        xps = [u["xp"] for u in users]
        assert xps == sorted(xps, reverse=True)
        for u in users:
            assert "level" in u and "badge_count" in u

    def test_users_me_xp_shape(self, maya):
        r = requests.get(f"{API}/users/me/xp", headers=H(maya["t"]), timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("xp", "level", "streak", "earned_badges", "all_badges", "recent_events"):
            assert k in d
        assert isinstance(d["all_badges"], list) and len(d["all_badges"]) >= 5

    def test_user_profile_has_level_and_badges(self):
        r = requests.get(f"{API}/users/maya", timeout=30)
        assert r.status_code == 200
        p = r.json()
        assert "level" in p and "name" in p["level"]
        assert "badges" in p and isinstance(p["badges"], list)


# ---------- XP rules + badges ----------
class TestXPRulesAndBadges:
    def test_post_create_awards_20_and_first_post_badge(self, freshuser):
        # initial xp from register includes daily_login (5)
        before = requests.get(f"{API}/users/me/xp", headers=H(freshuser["t"])).json()
        before_xp = before["xp"]
        before_badges = {b["key"] for b in before["earned_badges"]}
        r = requests.post(f"{API}/posts", json={
            "caption": "TEST_iter2 first", "media": "https://x/y.jpg", "media_type": "image", "tags": []
        }, headers=H(freshuser["t"]), timeout=30)
        assert r.status_code == 200
        after = requests.get(f"{API}/users/me/xp", headers=H(freshuser["t"])).json()
        assert after["xp"] >= before_xp + 20
        after_badges = {b["key"] for b in after["earned_badges"]}
        assert "first_post" in after_badges and "first_post" not in before_badges

    def test_gig_apply_15_and_earner_badge(self, freshuser):
        gigs = requests.get(f"{API}/gigs", timeout=30).json()
        gid = gigs[0]["id"]
        before = requests.get(f"{API}/users/me/xp", headers=H(freshuser["t"])).json()
        b_xp = before["xp"]
        r = requests.post(f"{API}/gigs/{gid}/apply", json={"message": "TEST"}, headers=H(freshuser["t"]), timeout=30)
        assert r.status_code == 200
        after = requests.get(f"{API}/users/me/xp", headers=H(freshuser["t"])).json()
        assert after["xp"] >= b_xp + 15
        keys = {b["key"] for b in after["earned_badges"]}
        assert "earner" in keys

    def test_enroll_awards_scholar(self, freshuser):
        # already enrolled in TestCourses but in case order differs
        courses = requests.get(f"{API}/courses", timeout=30).json()
        cid = courses[1]["id"]
        requests.post(f"{API}/courses/{cid}/enroll", headers=H(freshuser["t"]), timeout=30)
        keys = {b["key"] for b in requests.get(f"{API}/users/me/xp", headers=H(freshuser["t"])).json()["earned_badges"]}
        assert "scholar" in keys


# ---------- daily-login streak idempotency ----------
class TestStreak:
    def test_auth_me_does_not_double_count_same_day(self, freshuser):
        # call /auth/me twice, streak should not increment
        r1 = requests.get(f"{API}/auth/me", headers=H(freshuser["t"])).json()
        s1 = r1.get("streak", 0)
        time.sleep(0.5)
        r2 = requests.get(f"{API}/auth/me", headers=H(freshuser["t"])).json()
        assert r2.get("streak", 0) == s1
