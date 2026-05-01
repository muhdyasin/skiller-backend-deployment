"""Iteration 7 tests — Trial/Subscriptions, Wallet+Referrals, Stories, Community (groups+DMs)."""
import os
import time
import uuid
from pathlib import Path

import requests
import pytest
from dotenv import load_dotenv

# Load REACT_APP_BACKEND_URL from frontend/.env (single source of truth)
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set in frontend/.env"
API = f"{BASE_URL}/api"

DEMO = {"email": "maya@skiller.app", "password": "Demo@123"}
ARJUN = {"email": "arjun@skiller.app", "password": "Demo@123"}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def maya_token():
    return _login(**DEMO)


@pytest.fixture(scope="module")
def arjun_token():
    return _login(**ARJUN)


@pytest.fixture(scope="module")
def maya_me(maya_token):
    r = requests.get(f"{API}/auth/me", headers=_headers(maya_token), timeout=10)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Billing ----------
class TestBilling:
    def test_plans(self):
        r = requests.get(f"{API}/billing/plans", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["trial_days"] == 30
        assert data["referral_reward_tokens"] == 500
        ids = {p["id"]: p for p in data["plans"]}
        assert ids["trial_active"]["active"] is True
        assert ids["trial_active"]["price_inr"] == 299
        assert ids["trial_active"]["duration_days"] == 30
        assert ids["pro_quarterly"]["active"] is False
        assert ids["pro_quarterly"].get("coming_soon") is True
        assert ids["pro_yearly"]["active"] is False
        assert ids["pro_yearly"].get("coming_soon") is True

    def test_billing_me_demo_user(self, maya_token):
        r = requests.get(f"{API}/billing/me", headers=_headers(maya_token), timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "premium_until" in data
        assert data["is_premium"] is True
        assert data["days_left"] >= 25  # backfilled ~30d
        assert data["plan"] in ("trial", "pro")

    def test_checkout_razorpay_mock(self, maya_token):
        # iter9: Razorpay is now LIVE in test mode — should return order_created
        r = requests.post(
            f"{API}/billing/checkout",
            json={"plan_id": "trial_active", "pay_with": "razorpay"},
            headers=_headers(maya_token),
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "order_created"
        assert data["provider"] == "razorpay"
        assert data["order_id"].startswith("order_")
        assert data["amount"] == 29900

    def test_checkout_stripe_mock(self, maya_token):
        r = requests.post(
            f"{API}/billing/checkout",
            json={"plan_id": "trial_active", "pay_with": "stripe"},
            headers=_headers(maya_token),
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "mock"

    def test_checkout_tokens_insufficient(self):
        # Create fresh user (balance=0) to guarantee insufficient
        unique = uuid.uuid4().hex[:8]
        reg = requests.post(f"{API}/auth/register", json={
            "email": f"TEST_iter7_{unique}@example.com",
            "username": f"testit7{unique}",
            "name": "Test Iter7",
            "password": "Pass@1234",
            "role": "student",
        }, timeout=15)
        assert reg.status_code in (200, 201), reg.text
        tok = reg.json()["token"]
        r = requests.post(
            f"{API}/billing/checkout",
            json={"plan_id": "trial_active", "pay_with": "tokens"},
            headers=_headers(tok),
            timeout=10,
        )
        assert r.status_code == 400
        body = r.json()
        msg = (body.get("detail") or body.get("message") or "").lower()
        assert "insufficient" in msg or "balance" in msg


# ---------- Wallet ----------
class TestWallet:
    def test_wallet_me(self, maya_token):
        r = requests.get(f"{API}/wallet/me", headers=_headers(maya_token), timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "wallet" in data
        w = data["wallet"]
        for k in ("balance", "lifetime_earned", "lifetime_spent"):
            assert k in w
        assert data["reward_per_referral"] == 500
        rc = data["referral_code"]
        assert isinstance(rc, str) and len(rc) == 8 and rc.isupper()
        assert "ledger" in data
        assert "referrals" in data
        assert "stats" in data
        for k in ("total", "rewarded", "pending"):
            assert k in data["stats"]


# ---------- Referral end-to-end (token checkout flips referral status & rewards referrer) ----------
class TestReferralFlow:
    def test_full_referral_token_flow(self):
        from pymongo import MongoClient
        mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = mongo[os.environ.get("DB_NAME", "skiller_db")]

        u1 = uuid.uuid4().hex[:8]
        u2 = uuid.uuid4().hex[:8]
        # Register user1
        r1 = requests.post(f"{API}/auth/register", json={
            "email": f"TEST_ref_a_{u1}@example.com",
            "username": f"refa{u1}",
            "name": "Ref A",
            "password": "Pass@1234",
            "role": "student",
        }, timeout=15)
        assert r1.status_code in (200, 201), r1.text
        tok1 = r1.json()["token"]
        wallet1 = requests.get(f"{API}/wallet/me", headers=_headers(tok1), timeout=10).json()
        ref_code = wallet1["referral_code"]
        u1_id = r1.json()["user"]["id"] if "user" in r1.json() else requests.get(f"{API}/auth/me", headers=_headers(tok1), timeout=10).json()["id"]
        baseline_balance = wallet1["wallet"]["balance"]

        # Register user2 with referral_code
        r2 = requests.post(f"{API}/auth/register", json={
            "email": f"TEST_ref_b_{u2}@example.com",
            "username": f"refb{u2}",
            "name": "Ref B",
            "password": "Pass@1234",
            "role": "student",
            "referral_code": ref_code,
        }, timeout=15)
        assert r2.status_code in (200, 201), r2.text
        tok2 = r2.json()["token"]
        u2_me = requests.get(f"{API}/auth/me", headers=_headers(tok2), timeout=10).json()
        u2_id = u2_me["id"]

        # Verify referral row pending
        ref_row = db.referrals.find_one({"referrer_id": u1_id, "referred_user_id": u2_id})
        assert ref_row is not None, "Referral row not created on signup"
        assert ref_row["status"] == "pending"

        # Verify user2 has trial premium ~30d
        billing_u2 = requests.get(f"{API}/billing/me", headers=_headers(tok2), timeout=10).json()
        assert billing_u2["is_premium"] is True
        assert billing_u2["days_left"] >= 28

        # Seed user2 with 299 tokens directly (simulate earning) — wallet doc must exist; ensured by /wallet/me
        requests.get(f"{API}/wallet/me", headers=_headers(tok2), timeout=10)
        db.token_wallets.update_one(
            {"user_id": u2_id},
            {"$inc": {"balance": 299, "lifetime_earned": 299}},
        )

        # User2 buys subscription via tokens — should reward user1 with 500 tokens & flip referral
        r_co = requests.post(
            f"{API}/billing/checkout",
            json={"plan_id": "trial_active", "pay_with": "tokens"},
            headers=_headers(tok2),
            timeout=15,
        )
        assert r_co.status_code == 200, r_co.text
        co = r_co.json()
        assert co.get("status") == "paid"
        assert "new_until" in co

        # Check referral status
        ref_row2 = db.referrals.find_one({"referrer_id": u1_id, "referred_user_id": u2_id})
        assert ref_row2["status"] == "rewarded"

        # Check user1 wallet incremented by 500
        wallet1_after = requests.get(f"{API}/wallet/me", headers=_headers(tok1), timeout=10).json()
        assert wallet1_after["wallet"]["balance"] == baseline_balance + 500

        # User1 wallet ledger should have a referral credit
        reasons = [e.get("reason") for e in wallet1_after["ledger"]]
        assert "referral" in reasons


# ---------- Wallet redeem ----------
class TestRedeem:
    @pytest.fixture(scope="class")
    def funded_user(self):
        from pymongo import MongoClient
        mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = mongo[os.environ.get("DB_NAME", "skiller_db")]
        u = uuid.uuid4().hex[:8]
        r = requests.post(f"{API}/auth/register", json={
            "email": f"TEST_red_{u}@example.com",
            "username": f"red{u}",
            "name": "Red User",
            "password": "Pass@1234",
            "role": "student",
        }, timeout=15)
        assert r.status_code in (200, 201)
        tok = r.json()["token"]
        me = requests.get(f"{API}/auth/me", headers=_headers(tok), timeout=10).json()
        # Force wallet exist
        requests.get(f"{API}/wallet/me", headers=_headers(tok), timeout=10)
        db.token_wallets.update_one(
            {"user_id": me["id"]},
            {"$inc": {"balance": 1000, "lifetime_earned": 1000}},
        )
        return {"token": tok, "id": me["id"], "db": db}

    def test_redeem_ai_credits(self, funded_user):
        tok = funded_user["token"]
        uid = funded_user["id"]
        db = funded_user["db"]
        before = db.users.find_one({"id": uid}) or {}
        before_credits = before.get("ai_credits", 0)
        r = requests.post(
            f"{API}/wallet/redeem",
            json={"amount": 50, "purpose": "ai_credits"},
            headers=_headers(tok),
            timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["purpose"] == "ai_credits"
        after = db.users.find_one({"id": uid})
        assert after.get("ai_credits", 0) == before_credits + 50

    def test_redeem_ads(self, funded_user):
        tok = funded_user["token"]
        uid = funded_user["id"]
        db = funded_user["db"]
        r = requests.post(
            f"{API}/wallet/redeem",
            json={"amount": 25, "purpose": "ads"},
            headers=_headers(tok),
            timeout=10,
        )
        assert r.status_code == 200, r.text
        # Verify ads ledger entry
        entry = db.token_ledger.find_one({"user_id": uid, "reason": "ads"})
        assert entry is not None

    def test_redeem_course_requires_target(self, funded_user):
        tok = funded_user["token"]
        r = requests.post(
            f"{API}/wallet/redeem",
            json={"amount": 50, "purpose": "course"},
            headers=_headers(tok),
            timeout=10,
        )
        assert r.status_code == 400


# ---------- Stories ----------
class TestStories:
    def test_stories_feed(self, maya_token):
        r = requests.get(f"{API}/stories/feed", headers=_headers(maya_token), timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_view_delete_story(self, maya_token, arjun_token):
        # Create
        r = requests.post(
            f"{API}/stories",
            json={"media": "https://images.unsplash.com/photo-1.jpg",
                  "media_type": "image", "caption": "TEST"},
            headers=_headers(maya_token),
            timeout=10,
        )
        assert r.status_code == 200, r.text
        story = r.json()
        sid = story["id"]
        assert story["caption"] == "TEST"
        assert story.get("expires_at"), "expires_at missing"

        # Verify TTL ~24h
        from datetime import datetime, timezone
        exp = datetime.fromisoformat(story["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff_h = (exp - now).total_seconds() / 3600
        assert 23 < diff_h < 25, f"TTL not ~24h, got {diff_h}h"

        # View by arjun
        rv = requests.post(f"{API}/stories/{sid}/view", headers=_headers(arjun_token), timeout=10)
        assert rv.status_code == 200

        # Delete by arjun (should fail)
        rd_bad = requests.delete(f"{API}/stories/{sid}", headers=_headers(arjun_token), timeout=10)
        assert rd_bad.status_code == 404

        # Delete by maya
        rd = requests.delete(f"{API}/stories/{sid}", headers=_headers(maya_token), timeout=10)
        assert rd.status_code == 200

    def test_stories_ttl_index(self):
        from pymongo import MongoClient
        mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = mongo[os.environ.get("DB_NAME", "skiller_db")]
        idx = db.stories.index_information()
        ttl_idx = idx.get("expires_at_dt_1")
        assert ttl_idx is not None
        assert ttl_idx.get("expireAfterSeconds") == 0


# ---------- Community ----------
class TestCommunity:
    def test_create_dm_idempotent(self, maya_token):
        # Create DM with arjun
        r1 = requests.post(
            f"{API}/community/groups",
            json={"name": "DM", "is_dm": True, "member_usernames": ["arjun"]},
            headers=_headers(maya_token),
            timeout=10,
        )
        assert r1.status_code == 200, r1.text
        g1 = r1.json()
        assert g1["is_dm"] is True
        assert len(g1["members"]) == 2

        # Same again -> same group
        r2 = requests.post(
            f"{API}/community/groups",
            json={"name": "DM2", "is_dm": True, "member_usernames": ["arjun"]},
            headers=_headers(maya_token),
            timeout=10,
        )
        assert r2.status_code == 200
        assert r2.json()["id"] == g1["id"]

    def test_list_my_groups(self, maya_token):
        r = requests.get(f"{API}/community/groups", headers=_headers(maya_token), timeout=10)
        assert r.status_code == 200
        groups = r.json()
        assert isinstance(groups, list)
        for g in groups:
            assert "display_name" in g
            assert "unread" in g

    def test_send_message_react_read(self, maya_token, arjun_token):
        # Get/create DM
        r = requests.post(
            f"{API}/community/groups",
            json={"name": "DM", "is_dm": True, "member_usernames": ["arjun"]},
            headers=_headers(maya_token),
            timeout=10,
        )
        gid = r.json()["id"]

        # Maya sends text
        rs = requests.post(
            f"{API}/community/groups/{gid}/messages",
            json={"type": "text", "text": "hi from maya TEST"},
            headers=_headers(maya_token),
            timeout=10,
        )
        assert rs.status_code == 200
        msg = rs.json()
        mid = msg["id"]
        assert msg["text"] == "hi from maya TEST"
        assert "read_by" in msg

        # Arjun reacts ❤️
        rr = requests.post(
            f"{API}/community/groups/{gid}/messages/{mid}/react",
            json={"emoji": "❤️"},
            headers=_headers(arjun_token),
            timeout=10,
        )
        assert rr.status_code == 200, rr.text
        reacts = rr.json()["reactions"]
        assert "❤️" in reacts

        # Arjun reacts 🔥 (toggles off ❤️, adds 🔥)
        rr2 = requests.post(
            f"{API}/community/groups/{gid}/messages/{mid}/react",
            json={"emoji": "🔥"},
            headers=_headers(arjun_token),
            timeout=10,
        )
        assert rr2.status_code == 200
        reacts2 = rr2.json()["reactions"]
        assert "🔥" in reacts2
        assert "❤️" not in reacts2  # one emoji per user

        # Arjun marks read
        rk = requests.post(
            f"{API}/community/groups/{gid}/read",
            json={},
            headers=_headers(arjun_token),
            timeout=10,
        )
        assert rk.status_code == 200

        # Verify read_by includes arjun
        msgs = requests.get(
            f"{API}/community/groups/{gid}/messages",
            headers=_headers(maya_token),
            timeout=10,
        ).json()
        target = next((m for m in msgs if m["id"] == mid), None)
        assert target is not None
        arjun_id = next(s["sender_id"] for s in msgs if s["id"] == mid)  # placeholder
        # Get arjun's id via /auth/me
        a_me = requests.get(f"{API}/auth/me", headers=_headers(arjun_token), timeout=10).json()
        assert a_me["id"] in target["read_by"]

    def test_typing_endpoint(self, maya_token):
        r0 = requests.post(
            f"{API}/community/groups",
            json={"name": "DM", "is_dm": True, "member_usernames": ["arjun"]},
            headers=_headers(maya_token),
            timeout=10,
        )
        gid = r0.json()["id"]
        r = requests.post(
            f"{API}/community/groups/{gid}/typing",
            json={"typing": True},
            headers=_headers(maya_token),
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ---------- Search regression ----------
class TestSearch:
    def test_search_react(self, maya_token):
        r = requests.get(f"{API}/search?q=react", headers=_headers(maya_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # 4 buckets: users, posts, courses, gigs (or similar)
        assert isinstance(data, dict)
        assert len(data.keys()) >= 3
