"""Iteration 8 tests — SSR share wrappers, email verification flow, voice notes in chat."""
import os
import re
import time
import uuid
import subprocess
from pathlib import Path

import requests
import pytest
from dotenv import load_dotenv

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


def _headers(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def _mongo():
    from pymongo import MongoClient
    return MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[
        os.environ.get("DB_NAME", "skiller_db")
    ]


@pytest.fixture(scope="module")
def maya_token():
    return _login(**DEMO)


@pytest.fixture(scope="module")
def arjun_token():
    return _login(**ARJUN)


# ---------- SSR share wrappers ----------
class TestShareSSR:
    def _assert_og(self, html: str, must_contain_canonical_substr: str):
        for tag in ['property="og:title"', 'property="og:description"', 'property="og:image"',
                    'property="og:url"', 'name="twitter:card"', 'name="twitter:image"',
                    '<link rel="canonical"', 'http-equiv="refresh"']:
            assert tag in html, f"missing {tag}"
        assert must_contain_canonical_substr in html

    def test_share_creator_maya(self):
        r = requests.get(f"{API}/share/c/maya", timeout=15, allow_redirects=False)
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        html = r.text
        self._assert_og(html, "/c/maya")
        # body must show name + redirect link
        assert "Maya" in html
        assert "/c/maya" in html

    def test_share_creator_404(self):
        r = requests.get(f"{API}/share/c/nonexistent_xyz_{uuid.uuid4().hex[:6]}", timeout=10)
        assert r.status_code == 404

    def test_share_user_maya(self):
        r = requests.get(f"{API}/share/u/maya", timeout=15)
        assert r.status_code == 200
        self._assert_og(r.text, "/u/maya")
        assert "Maya" in r.text

    def test_share_post_uses_media_for_image(self):
        # find an image post
        db = _mongo()
        p = db.posts.find_one({"media_type": {"$ne": "video"}, "media": {"$ne": ""}}, {"_id": 0})
        if not p:
            pytest.skip("no image post in seed")
        r = requests.get(f"{API}/share/p/{p['id']}", timeout=15)
        assert r.status_code == 200
        html = r.text
        self._assert_og(html, f"/p/{p['id']}")
        # og:image should be the post media
        m = re.search(r'property="og:image" content="([^"]+)"', html)
        assert m and m.group(1) == p["media"]

    def test_share_post_video_uses_author_avatar(self):
        db = _mongo()
        p = db.posts.find_one({"media_type": "video"}, {"_id": 0})
        if not p:
            pytest.skip("no video post")
        author = db.users.find_one({"id": p["user_id"]}, {"_id": 0, "avatar_url": 1}) or {}
        r = requests.get(f"{API}/share/p/{p['id']}", timeout=15)
        assert r.status_code == 200
        m = re.search(r'property="og:image" content="([^"]+)"', r.text)
        assert m
        # should NOT be the post media (which is a video URL); it should be author avatar OR fallback
        assert m.group(1) != p.get("media", "x"), "video post should not use post.media as og:image"

    def test_share_post_404(self):
        r = requests.get(f"{API}/share/p/does_not_exist_{uuid.uuid4().hex[:6]}", timeout=10)
        assert r.status_code == 404

    def test_sitemap_regression(self):
        r = requests.get(f"{API}/sitemap.xml", timeout=10)
        assert r.status_code == 200
        assert "<urlset" in r.text


# ---------- Email verification ----------
class TestEmailVerification:
    @pytest.fixture(scope="class")
    def fresh_user(self):
        u = uuid.uuid4().hex[:8]
        email = f"test_iter8_{u}@example.com"  # lowercase: backend lowercases on insert
        r = requests.post(f"{API}/auth/register", json={
            "email": email,
            "username": f"iter8u{u}",
            "name": "Iter8 Tester",
            "password": "Pass@1234",
            "role": "student",
        }, timeout=15)
        assert r.status_code in (200, 201), r.text
        return {"email": email, "token": r.json()["token"]}

    def test_signup_creates_unverified_user_and_token(self, fresh_user):
        db = _mongo()
        u = db.users.find_one({"email": fresh_user["email"]}, {"_id": 0})
        assert u is not None
        assert u.get("email_verified") is False
        # token row should exist
        tok = db.email_verification_tokens.find_one({"user_id": u["id"], "used": False})
        assert tok is not None
        assert tok.get("token")
        assert tok.get("expires_at_dt") is not None

    def test_seeded_users_pre_verified(self):
        db = _mongo()
        for em in ("admin@skiller.app", "maya@skiller.app", "arjun@skiller.app", "neha@skiller.app"):
            u = db.users.find_one({"email": em}, {"_id": 0, "email_verified": 1})
            assert u and u.get("email_verified") is True, f"{em} should be pre-verified"

    def test_resend_already_verified(self, maya_token):
        r = requests.post(f"{API}/auth/resend-verification", headers=_headers(maya_token), timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True
        assert body.get("already_verified") is True

    def test_resend_rate_limited(self):
        # new user - first resend ok (will be 429 if a token was just issued at signup; we wait <60s and retry)
        u = uuid.uuid4().hex[:8]
        email = f"TEST_iter8rl_{u}@example.com"
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "username": f"rl{u}", "name": "RL", "password": "Pass@1234", "role": "student",
        }, timeout=15)
        assert r.status_code in (200, 201)
        tok = r.json()["token"]
        # A token was issued during registration (within last 1s) -> immediate resend should be 429
        r2 = requests.post(f"{API}/auth/resend-verification", headers=_headers(tok), timeout=10)
        assert r2.status_code == 429
        assert "minute" in (r2.json().get("detail", "")).lower()

    def test_verify_email_invalid_token(self):
        r = requests.post(f"{API}/auth/verify-email", json={"token": f"bogus_{uuid.uuid4().hex}"}, timeout=10)
        assert r.status_code == 400

    def test_verify_email_valid_token_sets_verified_and_awards_xp(self, fresh_user):
        db = _mongo()
        u = db.users.find_one({"email": fresh_user["email"]}, {"_id": 0})
        before_xp = u.get("xp", 0)
        tok = db.email_verification_tokens.find_one({"user_id": u["id"], "used": False})
        assert tok is not None
        token_str = tok["token"]

        r = requests.post(f"{API}/auth/verify-email", json={"token": token_str}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        u2 = db.users.find_one({"email": fresh_user["email"]}, {"_id": 0})
        assert u2.get("email_verified") is True
        assert u2.get("email_verified_at")
        # xp should have increased by at least 25 (could be more if events fire)
        assert u2.get("xp", 0) >= before_xp + 25, f"XP should increase by ≥25, was {before_xp}, now {u2.get('xp')}"
        # token marked used
        used = db.email_verification_tokens.find_one({"token": token_str})
        assert used.get("used") is True

    def test_verify_email_used_token_rejected(self, fresh_user):
        # Use the same token again -> 400
        db = _mongo()
        used_tok = db.email_verification_tokens.find_one({"user_id": db.users.find_one({"email": fresh_user["email"]})["id"], "used": True})
        if not used_tok:
            pytest.skip("no used token")
        r = requests.post(f"{API}/auth/verify-email", json={"token": used_tok["token"]}, timeout=10)
        assert r.status_code == 400


# ---------- Voice notes in chat ----------
class TestVoiceMessages:
    @pytest.fixture(scope="class")
    def dm(self, ):
        # Maya/Arjun DM (idempotent)
        maya = _login(**DEMO)
        r = requests.post(f"{API}/community/groups",
                          json={"name": "DM", "is_dm": True, "member_usernames": ["arjun"]},
                          headers=_headers(maya), timeout=10)
        assert r.status_code == 200
        return {"gid": r.json()["id"], "token": maya}

    def test_voice_message_create(self, dm):
        r = requests.post(
            f"{API}/community/groups/{dm['gid']}/messages",
            json={"type": "voice", "media": "https://example.com/test.webm", "duration_ms": 12000},
            headers=_headers(dm["token"]), timeout=10,
        )
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["type"] == "voice"
        assert m["media"] == "https://example.com/test.webm"
        assert m["duration_ms"] == 12000

    def test_group_last_message_preview_voice(self, dm):
        # send a voice
        requests.post(
            f"{API}/community/groups/{dm['gid']}/messages",
            json={"type": "voice", "media": "https://example.com/x.webm", "duration_ms": 5000},
            headers=_headers(dm["token"]), timeout=10,
        )
        # list groups, find this one, check preview
        gs = requests.get(f"{API}/community/groups", headers=_headers(dm["token"]), timeout=10).json()
        g = next((x for x in gs if x["id"] == dm["gid"]), None)
        assert g is not None
        assert g.get("last_message_preview", "").startswith("🎤")

    def test_voice_validation_no_media(self, dm):
        r = requests.post(
            f"{API}/community/groups/{dm['gid']}/messages",
            json={"type": "voice", "duration_ms": 1000},
            headers=_headers(dm["token"]), timeout=10,
        )
        assert r.status_code == 400
        assert "voice media required" in r.json().get("detail", "").lower()

    def test_text_message_regression(self, dm):
        r = requests.post(
            f"{API}/community/groups/{dm['gid']}/messages",
            json={"type": "text", "text": "regression text TEST"},
            headers=_headers(dm["token"]), timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["text"] == "regression text TEST"

    def test_image_message_regression(self, dm):
        r = requests.post(
            f"{API}/community/groups/{dm['gid']}/messages",
            json={"type": "image", "media": "https://example.com/p.jpg"},
            headers=_headers(dm["token"]), timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["type"] == "image"


# ---------- Group settings regression ----------
class TestGroupSettingsRegression:
    def test_patch_and_member_ops(self):
        maya = _login(**DEMO)
        arjun = _login(**ARJUN)
        # create a fresh group
        r = requests.post(f"{API}/community/groups",
                          json={"name": "TEST_iter8_grp", "is_dm": False, "member_usernames": ["arjun"]},
                          headers=_headers(maya), timeout=10)
        assert r.status_code == 200
        gid = r.json()["id"]

        # rename
        r = requests.patch(f"{API}/community/groups/{gid}",
                           json={"name": "TEST_iter8_grp_renamed", "description": "d"},
                           headers=_headers(maya), timeout=10)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_iter8_grp_renamed"

        # non-admin patch -> 403
        r = requests.patch(f"{API}/community/groups/{gid}",
                           json={"name": "hax"},
                           headers=_headers(arjun), timeout=10)
        assert r.status_code in (403, 401)

        # add neha as member (admin)
        r = requests.post(f"{API}/community/groups/{gid}/members",
                          json={"username": "neha"}, headers=_headers(maya), timeout=10)
        assert r.status_code == 200

        # arjun self-leaves (delete on self)
        a_me = requests.get(f"{API}/auth/me", headers=_headers(arjun), timeout=10).json()
        r = requests.delete(f"{API}/community/groups/{gid}/members/{a_me['id']}",
                            headers=_headers(arjun), timeout=10)
        assert r.status_code == 200
