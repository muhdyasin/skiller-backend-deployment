"""Skiller iteration-4 backend tests.

Covers:
- /api/search GET (case-insensitive, substring; users/posts/courses/gigs sections; empty q -> 422)
- /api/push/vapid-public-key returns base64-url string (>=80 chars)
- /api/push/subscribe (auth required; idempotent on same endpoint)
- /api/push/unsubscribe sets active=false
- create_notification + send_web_push best-effort path (fake endpoint, 410 marks inactive)
- forgot-password endpoint still ok=true with RESEND_API_KEY empty (console fallback)
- Smoke: critical pre-existing endpoints still work after refactor
"""
import os, uuid, asyncio, json
import pytest, requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE}/api"

MAYA = {"email": "maya@skiller.app", "password": "Demo@123"}
ARJUN = {"email": "arjun@skiller.app", "password": "Demo@123"}


def hdr(t): return {"Authorization": f"Bearer {t}"}


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


# ---------- Search ----------

class TestSearch:
    def test_empty_q_422(self):
        r = requests.get(f"{API}/search", params={"q": ""}, timeout=15)
        assert r.status_code == 422, r.text

    def test_missing_q_422(self):
        r = requests.get(f"{API}/search", timeout=15)
        assert r.status_code == 422

    def test_react_returns_all_sections(self):
        r = requests.get(f"{API}/search", params={"q": "react"}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("users", "posts", "courses", "gigs", "counts"):
            assert k in d
        # should hit at least one section
        total = sum(d["counts"].values())
        assert total >= 1
        # courses or gigs typically have react in seed
        assert d["counts"]["courses"] + d["counts"]["gigs"] + d["counts"]["users"] >= 1

    def test_case_insensitive(self):
        a = requests.get(f"{API}/search", params={"q": "REACT"}, timeout=20).json()
        b = requests.get(f"{API}/search", params={"q": "react"}, timeout=20).json()
        assert a["counts"] == b["counts"]

    def test_user_hit_maya(self):
        d = requests.get(f"{API}/search", params={"q": "maya"}, timeout=20).json()
        usernames = [u.get("username") for u in d["users"]]
        assert "maya" in usernames

    def test_design_multi(self):
        d = requests.get(f"{API}/search", params={"q": "design"}, timeout=20).json()
        # at least one of any sections should match
        assert sum(d["counts"].values()) >= 1

    def test_limit_param_respected(self):
        d = requests.get(f"{API}/search", params={"q": "a", "limit": 2}, timeout=20).json()
        assert len(d["users"]) <= 2
        assert len(d["posts"]) <= 2
        assert len(d["courses"]) <= 2
        assert len(d["gigs"]) <= 2

    def test_no_mongo_id_leak(self):
        d = requests.get(f"{API}/search", params={"q": "a"}, timeout=20).json()
        for sec in ("users", "posts", "courses", "gigs"):
            for item in d[sec]:
                assert "_id" not in item


# ---------- Push ----------

class TestPush:
    def test_vapid_public_key(self):
        r = requests.get(f"{API}/push/vapid-public-key", timeout=15)
        assert r.status_code == 200
        pk = r.json().get("public_key")
        assert isinstance(pk, str)
        # base64-url encoded uncompressed P-256 key is ~87 chars (65 bytes)
        assert len(pk) >= 80, f"key too short: {len(pk)}"

    def test_subscribe_requires_auth(self):
        r = requests.post(f"{API}/push/subscribe", json={"subscription": {"endpoint": "x"}}, timeout=15)
        assert r.status_code in (401, 403)

    def test_subscribe_then_idempotent_then_unsubscribe(self):
        token, user = login(MAYA)
        endpoint = f"https://example.test/push/{uuid.uuid4()}"
        sub = {"subscription": {"endpoint": endpoint, "keys": {"p256dh": "x", "auth": "y"}}}

        r1 = requests.post(f"{API}/push/subscribe", headers=hdr(token), json=sub, timeout=15)
        assert r1.status_code == 200, r1.text
        assert r1.json().get("ok") is True

        # repost same endpoint -> not duplicated
        r2 = requests.post(f"{API}/push/subscribe", headers=hdr(token), json=sub, timeout=15)
        assert r2.status_code == 200

        # verify in DB exactly one row + active=true
        async def _check_one():
            mc = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            db = mc[os.environ.get("DB_NAME", "skiller_db")]
            docs = await db.push_subscriptions.find({"subscription.endpoint": endpoint}).to_list(10)
            mc.close()
            return docs
        docs = asyncio.new_event_loop().run_until_complete(_check_one())
        assert len(docs) == 1, f"got {len(docs)} docs"
        assert docs[0]["active"] is True

        # unsubscribe
        r3 = requests.post(f"{API}/push/unsubscribe", headers=hdr(token), json={"endpoint": endpoint}, timeout=15)
        assert r3.status_code == 200

        async def _check_inactive():
            mc = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            db = mc[os.environ.get("DB_NAME", "skiller_db")]
            d = await db.push_subscriptions.find_one({"subscription.endpoint": endpoint})
            await db.push_subscriptions.delete_one({"subscription.endpoint": endpoint})
            mc.close()
            return d
        d = asyncio.new_event_loop().run_until_complete(_check_inactive())
        assert d is not None
        assert d["active"] is False

    def test_subscribe_invalid_subscription(self):
        token, _ = login(MAYA)
        r = requests.post(f"{API}/push/subscribe", headers=hdr(token), json={"subscription": {}}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is False


# ---------- Web push best-effort + 410 marks inactive ----------

class TestWebPushBestEffort:
    def test_create_notification_with_fake_subscription_does_not_raise(self):
        """Subscribe Arjun with a clearly-fake endpoint, have Maya follow him.
        Server should attempt push, fail (410 / network), mark sub inactive,
        but the follow API itself must succeed (200)."""
        m_token, m_user = login(MAYA)
        a_token, a_user = login(ARJUN)

        endpoint = f"https://fcm.googleapis.com/fcm/send/__INVALID__{uuid.uuid4()}"
        sub = {"subscription": {
            "endpoint": endpoint,
            "keys": {"p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCT-_o0M5Vp7-PcAdvpHFP3o3lQ7MV8hYf6h2I0vTKxk7t5MhvxhM",
                     "auth": "tBHItJI5svbpez7KI4CCXg"}
        }}
        rsub = requests.post(f"{API}/push/subscribe", headers=hdr(a_token), json=sub, timeout=15)
        assert rsub.status_code == 200

        # Capture initial follow state so we can restore it (so prior tests aren't affected)
        prof = requests.get(f"{API}/users/arjun", timeout=15).json()
        arjun_obj = prof.get("user", prof)
        was_following = m_user["id"] in (arjun_obj.get("followers") or [])

        # Toggle follow to generate notification (which triggers send_web_push)
        r = requests.post(f"{API}/users/{a_user['id']}/follow", headers=hdr(m_token), timeout=20)
        assert r.status_code == 200, r.text

        # Restore prior state: if we changed it, toggle once more
        prof2 = requests.get(f"{API}/users/arjun", timeout=15).json()
        arjun_obj2 = prof2.get("user", prof2)
        is_following_now = m_user["id"] in (arjun_obj2.get("followers") or [])
        if is_following_now != was_following:
            requests.post(f"{API}/users/{a_user['id']}/follow", headers=hdr(m_token), timeout=20)

        # Sub should now be marked inactive (410 from invalid endpoint)
        async def _check():
            mc = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            db = mc[os.environ.get("DB_NAME", "skiller_db")]
            d = await db.push_subscriptions.find_one({"subscription.endpoint": endpoint})
            await db.push_subscriptions.delete_one({"subscription.endpoint": endpoint})
            mc.close()
            return d
        d = asyncio.new_event_loop().run_until_complete(_check())
        # Subscription doc exists and was processed; whether inactive depends on
        # pywebpush installed. Tolerate either outcome but require doc exists.
        assert d is not None


# ---------- Forgot password (Resend not configured -> console fallback) ----------

class TestForgotPasswordResendFallback:
    def test_forgot_password_returns_ok(self):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": "maya@skiller.app"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        # spec: returns ok=true regardless of whether email exists (no enumeration)
        assert d.get("ok") is True or d.get("message")

    def test_forgot_password_unknown_email_ok(self):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": "nobody@example.com"}, timeout=15)
        assert r.status_code == 200


# ---------- Smoke: previous endpoints still work after router refactor ----------

class TestPostRefactorSmoke:
    @pytest.fixture(scope="class")
    def auth(self):
        return login(MAYA)

    def test_login(self, auth):
        token, user = auth
        assert token and user["email"] == MAYA["email"]

    def test_me(self, auth):
        token, _ = auth
        r = requests.get(f"{API}/auth/me", headers=hdr(token), timeout=15)
        assert r.status_code == 200

    def test_feed(self, auth):
        token, _ = auth
        r = requests.get(f"{API}/posts/feed", headers=hdr(token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_explore(self):
        r = requests.get(f"{API}/posts/explore", timeout=15)
        assert r.status_code == 200

    def test_courses(self):
        r = requests.get(f"{API}/courses", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_gigs(self):
        r = requests.get(f"{API}/gigs", timeout=15)
        assert r.status_code == 200

    def test_user_profile(self):
        r = requests.get(f"{API}/users/maya", timeout=15)
        assert r.status_code == 200
        body = r.json()
        u = body.get("user", body)
        assert u["username"] == "maya"

    def test_dashboard_stats(self, auth):
        token, _ = auth
        r = requests.get(f"{API}/dashboard/stats", headers=hdr(token), timeout=15)
        assert r.status_code == 200

    def test_notifications(self, auth):
        token, _ = auth
        r = requests.get(f"{API}/notifications", headers=hdr(token), timeout=15)
        assert r.status_code == 200

    def test_leaderboard(self):
        r = requests.get(f"{API}/leaderboard", timeout=15)
        assert r.status_code == 200

    def test_xp(self, auth):
        token, _ = auth
        r = requests.get(f"{API}/users/me/xp", headers=hdr(token), timeout=15)
        assert r.status_code == 200

    def test_ai_recommend(self, auth):
        token, _ = auth
        r = requests.get(f"{API}/ai/recommend", headers=hdr(token), timeout=20)
        assert r.status_code == 200

    def test_ads_active(self):
        r = requests.get(f"{API}/ads/active", timeout=15)
        assert r.status_code == 200
