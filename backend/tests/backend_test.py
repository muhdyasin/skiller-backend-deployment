"""Skiller backend pytest suite - covers auth, posts, users, courses, gigs."""
import os, uuid, base64
import pytest, requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    # fallback to frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE}/api"

DEMO = {"email": "maya@skiller.app", "password": "Demo@123"}
ARJUN = {"email": "arjun@skiller.app", "password": "Demo@123"}

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
).decode()


@pytest.fixture(scope="session")
def maya_token():
    r = requests.post(f"{API}/auth/login", json=DEMO, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def arjun_token():
    r = requests.post(f"{API}/auth/login", json=ARJUN, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def hdr(t): return {"Authorization": f"Bearer {t}"}


# ---------- AUTH ----------
class TestAuth:
    def test_login_success(self):
        r = requests.post(f"{API}/auth/login", json=DEMO, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "token" in d and isinstance(d["token"], str)
        assert d["user"]["email"] == DEMO["email"]
        assert d["user"]["username"] == "maya"
        assert "_id" not in d["user"]
        assert "password_hash" not in d["user"]

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": DEMO["email"], "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_me(self, maya_token):
        r = requests.get(f"{API}/auth/me", headers=hdr(maya_token), timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == DEMO["email"]

    def test_me_no_token(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_register_and_duplicate(self):
        suf = uuid.uuid4().hex[:8]
        payload = {"email": f"test_{suf}@skiller.app", "password": "Test@1234",
                   "name": "Test User", "username": f"test_{suf}"}
        r = requests.post(f"{API}/auth/register", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "token" in d and d["user"]["email"] == payload["email"]
        # duplicate email
        r2 = requests.post(f"{API}/auth/register", json=payload, timeout=15)
        assert r2.status_code == 400


# ---------- POSTS ----------
class TestPosts:
    def test_feed(self):
        r = requests.get(f"{API}/posts/feed", timeout=15)
        assert r.status_code == 200
        posts = r.json()
        assert isinstance(posts, list) and len(posts) >= 6
        p = posts[0]
        for k in ("id", "author", "like_count", "comment_count", "media", "caption"):
            assert k in p
        assert "_id" not in p
        assert p["author"] is not None and "username" in p["author"]

    def test_explore(self):
        r = requests.get(f"{API}/posts/explore", timeout=15)
        assert r.status_code == 200 and isinstance(r.json(), list)

    def test_create_like_comment(self, maya_token, arjun_token):
        # create
        r = requests.post(f"{API}/posts", headers=hdr(maya_token),
                          json={"caption": "TEST_post", "media": PNG_DATA_URL,
                                "media_type": "image", "tags": ["test"]}, timeout=15)
        assert r.status_code == 200, r.text
        post = r.json()
        pid = post["id"]
        assert post["like_count"] == 0 and post["comment_count"] == 0

        # like by arjun
        r = requests.post(f"{API}/posts/{pid}/like", headers=hdr(arjun_token), timeout=15)
        assert r.status_code == 200
        assert r.json() == {"liked": True, "like_count": 1}
        # toggle off
        r = requests.post(f"{API}/posts/{pid}/like", headers=hdr(arjun_token), timeout=15)
        assert r.json()["liked"] is False and r.json()["like_count"] == 0

        # comment
        r = requests.post(f"{API}/posts/{pid}/comments", headers=hdr(arjun_token),
                          json={"text": "TEST_comment"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["text"] == "TEST_comment"

        # verify via GET
        r = requests.get(f"{API}/posts/{pid}", timeout=15)
        assert r.status_code == 200
        assert r.json()["comment_count"] == 1

        # cleanup
        requests.delete(f"{API}/posts/{pid}", headers=hdr(maya_token), timeout=15)

    def test_create_no_auth(self):
        r = requests.post(f"{API}/posts", json={"media": PNG_DATA_URL}, timeout=15)
        assert r.status_code == 401


# ---------- USERS ----------
class TestUsers:
    def test_get_profile(self):
        r = requests.get(f"{API}/users/maya", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("user", "posts", "post_count", "follower_count", "following_count", "is_following", "is_self"):
            assert k in d
        assert d["user"]["username"] == "maya"
        assert d["is_self"] is False

    def test_get_profile_self(self, maya_token):
        r = requests.get(f"{API}/users/maya", headers=hdr(maya_token), timeout=15)
        assert r.status_code == 200 and r.json()["is_self"] is True

    def test_follow_toggle(self, maya_token, arjun_token):
        # find arjun id
        arjun = requests.get(f"{API}/users/arjun", timeout=15).json()["user"]
        aid = arjun["id"]
        # maya follows arjun
        r = requests.post(f"{API}/users/{aid}/follow", headers=hdr(maya_token), timeout=15)
        assert r.status_code == 200 and r.json()["following"] is True
        # verify
        r = requests.get(f"{API}/users/arjun", headers=hdr(maya_token), timeout=15)
        assert r.json()["is_following"] is True
        # unfollow
        r = requests.post(f"{API}/users/{aid}/follow", headers=hdr(maya_token), timeout=15)
        assert r.json()["following"] is False

    def test_update_profile(self, maya_token):
        new_bio = f"TEST_bio_{uuid.uuid4().hex[:6]}"
        r = requests.patch(f"{API}/users/me", headers=hdr(maya_token),
                           json={"bio": new_bio}, timeout=15)
        assert r.status_code == 200 and r.json()["bio"] == new_bio
        # restore
        requests.patch(f"{API}/users/me", headers=hdr(maya_token),
                       json={"bio": "UI/UX designer · Bangalore. Turning ideas into pixels."}, timeout=15)


# ---------- COURSES & GIGS ----------
class TestCoursesGigs:
    def test_courses(self):
        r = requests.get(f"{API}/courses", timeout=15)
        assert r.status_code == 200
        c = r.json()
        assert isinstance(c, list) and len(c) == 4
        assert all("_id" not in x for x in c)
        assert all("title" in x and "price" in x for x in c)

    def test_gigs(self):
        r = requests.get(f"{API}/gigs", timeout=15)
        assert r.status_code == 200
        g = r.json()
        assert isinstance(g, list) and len(g) == 5

    def test_gig_apply(self, maya_token):
        gigs = requests.get(f"{API}/gigs", timeout=15).json()
        gid = gigs[0]["id"]
        r = requests.post(f"{API}/gigs/{gid}/apply", headers=hdr(maya_token),
                          json={"message": "TEST_application"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True and d["application"]["gig_id"] == gid

    def test_gig_apply_no_auth(self):
        gigs = requests.get(f"{API}/gigs", timeout=15).json()
        r = requests.post(f"{API}/gigs/{gigs[0]['id']}/apply", json={"message": "x"}, timeout=15)
        assert r.status_code == 401
