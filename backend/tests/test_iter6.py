"""Iteration 6 tests:
- /api/c/{username} (creator storefront)
- /api/search hybrid (text + regex)
- /api/auth/forgot-password TTL token shape + reset flow
- TTL/text indexes presence
- Regression smoke for previously-passing endpoints.
"""
import os
import pytest
import requests
from pathlib import Path
from pymongo import MongoClient


def _load_env(p: Path):
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env(Path("/app/frontend/.env"))
_load_env(Path("/app/backend/.env"))

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def maya_token(s):
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": "maya@skiller.app", "password": "Demo@123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": "admin@skiller.app", "password": "Admin@123"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


# ------------------ Storefront /api/c/{username} ------------------

class TestCreatorStorefront:
    def test_storefront_admin(self, s):
        r = s.get(f"{BASE_URL}/api/c/admin")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("user", "stats", "level", "badges", "courses", "gigs",
                  "reels", "posts", "is_following", "is_self"):
            assert k in d, f"missing key: {k}"
        # leak checks
        assert "_id" not in d["user"]
        assert "password_hash" not in d["user"]
        assert "followers" not in d["user"]
        assert "following" not in d["user"]
        # stats are counts not arrays
        assert isinstance(d["stats"]["followers"], int)
        assert isinstance(d["stats"]["following"], int)

    def test_storefront_maya(self, s):
        r = s.get(f"{BASE_URL}/api/c/maya")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["username"] == "maya"
        assert d["user"]["role"] in ("creator", "admin")
        # spec: maya has 1 course, 2 gigs, 1 reel, 2 posts
        assert d["stats"]["courses"] >= 1
        assert d["stats"]["gigs"] >= 2
        assert len(d["reels"]) >= 1
        assert len(d["posts"]) >= 2

    def test_storefront_arjun(self, s):
        r = s.get(f"{BASE_URL}/api/c/arjun")
        assert r.status_code == 200
        assert r.json()["user"]["role"] in ("creator", "admin")

    def test_storefront_neha(self, s):
        r = s.get(f"{BASE_URL}/api/c/neha")
        assert r.status_code == 200
        assert r.json()["user"]["role"] in ("creator", "admin")

    def test_storefront_404(self, s):
        r = s.get(f"{BASE_URL}/api/c/this_user_does_not_exist_xyz")
        assert r.status_code == 404

    def test_storefront_courses_have_enrollments(self, s):
        r = s.get(f"{BASE_URL}/api/c/maya")
        assert r.status_code == 200
        for c in r.json()["courses"]:
            assert "enrollments" in c
            assert isinstance(c["enrollments"], int)


# ------------------ Search hybrid ------------------

class TestSearchHybrid:
    def test_search_full_word_react(self, s):
        r = s.get(f"{BASE_URL}/api/search", params={"q": "react"})
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("users", "posts", "courses", "gigs", "counts"):
            assert k in d
        # at least one bucket non-empty for a seeded keyword
        total = sum(d["counts"].values())
        assert total > 0, f"expected results for 'react', got {d['counts']}"

    def test_search_short_partial_re(self, s):
        # 're' is too short for $text but regex fallback should work
        r = s.get(f"{BASE_URL}/api/search", params={"q": "re"})
        assert r.status_code == 200
        d = r.json()
        total = sum(d["counts"].values())
        assert total > 0, f"regex fallback returned nothing for 're'"

    def test_search_partial_may(self, s):
        r = s.get(f"{BASE_URL}/api/search", params={"q": "may"})
        assert r.status_code == 200
        d = r.json()
        # should match maya via regex fallback
        usernames = [u.get("username") for u in d["users"]]
        assert "maya" in usernames or sum(d["counts"].values()) > 0


# ------------------ Forgot/Reset password ------------------

class TestPasswordReset:
    def test_forgot_inserts_dual_field_token(self, s):
        # use neha to keep maya creds clean
        email = "neha@skiller.app"
        r = s.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": email})
        assert r.status_code == 200

        client = MongoClient(MONGO_URL)
        coll = client[DB_NAME].password_reset_tokens
        # find latest token for neha
        user = client[DB_NAME].users.find_one({"email": email})
        rec = coll.find_one({"user_id": user["id"], "used": False},
                            sort=[("created_at", -1)])
        assert rec is not None, "no reset token doc inserted"
        assert "expires_at" in rec and isinstance(rec["expires_at"], str)
        assert "expires_at_dt" in rec  # datetime — used by TTL
        # cleanup so neha's password remains intact (don't actually reset)
        coll.update_one({"_id": rec["_id"]}, {"$set": {"used": True}})
        client.close()

    def test_ttl_index_present(self):
        client = MongoClient(MONGO_URL)
        info = client[DB_NAME].password_reset_tokens.index_information()
        client.close()
        # any index keyed on expires_at_dt with expireAfterSeconds
        ttl = [n for n, v in info.items()
               if "expireAfterSeconds" in v and any(k[0] == "expires_at_dt" for k in v["key"])]
        assert ttl, f"TTL index missing on expires_at_dt. got: {list(info.keys())}"

    def test_reset_flow_end_to_end(self, s):
        # Use a unique throwaway TEST_ user per run
        import uuid as _uuid
        suffix = _uuid.uuid4().hex[:8]
        email = f"test_iter6_reset_{suffix}@skiller.app"
        username = f"test_iter6_reset_{suffix}"
        rr = s.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "username": username,
            "name": "Iter6 Reset", "password": "Init@123", "role": "student",
        })
        assert rr.status_code == 200, rr.text
        # forgot-password
        r = s.post(f"{BASE_URL}/api/auth/forgot-password", json={"email": email})
        assert r.status_code == 200

        # fetch token from DB
        client = MongoClient(MONGO_URL)
        user = client[DB_NAME].users.find_one({"email": email})
        assert user is not None, "registered user not found in DB"
        rec = client[DB_NAME].password_reset_tokens.find_one(
            {"user_id": user["id"], "used": False}, sort=[("created_at", -1)])
        client.close()
        assert rec, "token not found"
        token = rec["token"]

        # reset
        r2 = s.post(f"{BASE_URL}/api/auth/reset-password", json={
            "token": token, "new_password": "NewPass@123"
        })
        assert r2.status_code == 200, r2.text

        # login with new password
        r3 = s.post(f"{BASE_URL}/api/auth/login", json={
            "email": email, "password": "NewPass@123"
        })
        assert r3.status_code == 200


# ------------------ Text index presence ------------------

class TestTextIndexes:
    def test_text_indexes_exist(self):
        client = MongoClient(MONGO_URL)
        for coll in ("users", "posts", "courses", "gigs"):
            info = client[DB_NAME][coll].index_information()
            text_idxs = [n for n, v in info.items()
                         if any(k[1] == "text" for k in v["key"])]
            assert text_idxs, f"no text index on {coll}: {list(info.keys())}"
        client.close()


# ------------------ Regression: previously-passing endpoints ------------------

class TestRegression:
    def test_login(self, s):
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": "maya@skiller.app", "password": "Demo@123"})
        assert r.status_code == 200

    def test_me(self, s, maya_token):
        r = s.get(f"{BASE_URL}/api/auth/me",
                  headers={"Authorization": f"Bearer {maya_token}"})
        assert r.status_code == 200
        assert r.json()["email"] == "maya@skiller.app"

    def test_feed(self, s, maya_token):
        r = s.get(f"{BASE_URL}/api/posts/feed",
                  headers={"Authorization": f"Bearer {maya_token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_reels(self, s):
        r = s.get(f"{BASE_URL}/api/posts/reels")
        assert r.status_code == 200
        for p in r.json():
            assert p.get("media_type") == "video"

    def test_insights_creator_only(self, s, maya_token):
        r = s.get(f"{BASE_URL}/api/dashboard/insights",
                  headers={"Authorization": f"Bearer {maya_token}"})
        assert r.status_code == 200
        d = r.json()
        # spec mentioned series + top_posts/top_courses/ads/totals
        for k in ("series", "totals"):
            assert k in d, f"insights missing {k}: {list(d.keys())}"

    def test_crm(self, s, maya_token):
        r = s.get(f"{BASE_URL}/api/dashboard/crm",
                  headers={"Authorization": f"Bearer {maya_token}"})
        assert r.status_code == 200
