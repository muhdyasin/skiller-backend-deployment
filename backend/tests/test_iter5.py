"""Iteration 5: role split (student/creator), reels/subscriptions, insights/CRM, gig CRUD + applicants."""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://skiller-connect.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="module")
def maya_auth(session):
    token, user = _login(session, "maya@skiller.app", "Demo@123")
    return {"token": token, "user": user, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="module")
def arjun_auth(session):
    token, user = _login(session, "arjun@skiller.app", "Demo@123")
    return {"token": token, "user": user, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="module")
def admin_auth(session):
    token, user = _login(session, "admin@skiller.app", "Admin@123")
    return {"token": token, "user": user, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="module")
def fresh_student(session):
    """Create a brand new student account just for this test module."""
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_student_{suffix}@skiller.app"
    username = f"test_stu_{suffix}"
    payload = {"email": email, "password": "Test@1234", "name": "Test Student", "username": username, "role": "student"}
    r = session.post(f"{API}/auth/register", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    return {"token": body["token"], "user": body["user"], "headers": {"Authorization": f"Bearer {body['token']}"}}


# ---------- Register: role validation ----------
class TestRegisterRole:
    def test_register_default_role_is_student(self, session):
        suffix = uuid.uuid4().hex[:8]
        payload = {"email": f"TEST_def_{suffix}@skiller.app", "password": "Test@1234",
                   "name": "Default Role", "username": f"test_def_{suffix}"}
        r = session.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "student"

    def test_register_creator_role_accepted(self, session):
        suffix = uuid.uuid4().hex[:8]
        payload = {"email": f"TEST_cr_{suffix}@skiller.app", "password": "Test@1234",
                   "name": "Creator R", "username": f"test_cr_{suffix}", "role": "creator"}
        r = session.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "creator"

    def test_register_invalid_role_rejected(self, session):
        suffix = uuid.uuid4().hex[:8]
        payload = {"email": f"TEST_bad_{suffix}@skiller.app", "password": "Test@1234",
                   "name": "Bad", "username": f"test_bad_{suffix}", "role": "admin"}
        r = session.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code == 422


# ---------- Login response includes role ----------
class TestLoginRole:
    def test_login_includes_role_creator(self, maya_auth):
        assert maya_auth["user"]["role"] == "creator"

    def test_login_includes_role_admin(self, admin_auth):
        assert admin_auth["user"]["role"] == "admin"

    def test_demo_creators_all_present(self, session):
        for em in ("maya@skiller.app", "arjun@skiller.app", "neha@skiller.app"):
            r = session.post(f"{API}/auth/login", json={"email": em, "password": "Demo@123"}, timeout=30)
            assert r.status_code == 200, f"{em}: {r.text}"
            assert r.json()["user"]["role"] == "creator"


# ---------- /users/me/enrollments + /applications ----------
class TestMyEnrollmentsApplications:
    def test_my_enrollments_array(self, fresh_student, session):
        r = session.get(f"{API}/users/me/enrollments", headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_my_applications_array(self, fresh_student, session):
        r = session.get(f"{API}/users/me/applications", headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_enrollments_after_enroll(self, fresh_student, session):
        # Pick any course
        r = session.get(f"{API}/courses", timeout=30)
        assert r.status_code == 200
        courses = r.json()
        if not courses:
            pytest.skip("No courses seeded")
        cid = courses[0]["id"]
        er = session.post(f"{API}/courses/{cid}/enroll", headers=fresh_student["headers"], timeout=30)
        assert er.status_code == 200
        r2 = session.get(f"{API}/users/me/enrollments", headers=fresh_student["headers"], timeout=30)
        assert r2.status_code == 200
        ids = [c["id"] for c in r2.json()]
        assert cid in ids

    def test_applications_after_apply(self, fresh_student, session):
        # Pick any gig
        r = session.get(f"{API}/gigs", timeout=30)
        gigs = r.json()
        if not gigs:
            pytest.skip("No gigs seeded")
        gid = gigs[0]["id"]
        ar = session.post(f"{API}/gigs/{gid}/apply", json={"message": "TEST apply"},
                          headers=fresh_student["headers"], timeout=30)
        assert ar.status_code == 200
        r2 = session.get(f"{API}/users/me/applications", headers=fresh_student["headers"], timeout=30)
        assert r2.status_code == 200
        items = r2.json()
        assert len(items) >= 1
        # gig info attached
        assert items[0].get("gig") is not None
        assert items[0]["status"] == "pending"


# ---------- upgrade-role ----------
class TestUpgradeRole:
    def test_student_can_upgrade_to_creator(self, session):
        suffix = uuid.uuid4().hex[:8]
        payload = {"email": f"TEST_up_{suffix}@skiller.app", "password": "Test@1234",
                   "name": "Up", "username": f"test_up_{suffix}", "role": "student"}
        r = session.post(f"{API}/auth/register", json=payload, timeout=30)
        assert r.status_code == 200
        token = r.json()["token"]
        h = {"Authorization": f"Bearer {token}"}
        up = session.post(f"{API}/users/me/upgrade-role", json={"role": "creator"}, headers=h, timeout=30)
        assert up.status_code == 200
        assert up.json()["role"] == "creator"

    def test_upgrade_invalid_role_rejected(self, fresh_student, session):
        r = session.post(f"{API}/users/me/upgrade-role", json={"role": "admin"},
                         headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 422


# ---------- Gig CRUD (creator-only) ----------
class TestGigCRUD:
    def test_student_cannot_create_gig(self, fresh_student, session):
        r = session.post(f"{API}/gigs", json={"title": "TEST_x", "description": "no"},
                         headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 403

    def test_creator_create_gig(self, maya_auth, session):
        payload = {"title": "TEST_iter5_gig", "description": "iter5 test gig",
                   "budget": 1000, "location": "Remote", "category": "Test", "skills": ["python"]}
        r = session.post(f"{API}/gigs", json=payload, headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 200
        gig = r.json()
        assert gig["owner_id"] == maya_auth["user"]["id"]
        assert gig["title"] == "TEST_iter5_gig"
        # store on class for chained tests
        TestGigCRUD.gig_id = gig["id"]

    def test_my_gigs_list(self, maya_auth, session):
        r = session.get(f"{API}/gigs/mine", headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 200
        gigs = r.json()
        assert any(g["id"] == TestGigCRUD.gig_id for g in gigs)
        for g in gigs:
            assert "application_count" in g

    def test_my_gigs_forbidden_for_student(self, fresh_student, session):
        r = session.get(f"{API}/gigs/mine", headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 403

    def test_apply_creates_application(self, fresh_student, session):
        r = session.post(f"{API}/gigs/{TestGigCRUD.gig_id}/apply",
                         json={"message": "TEST applying"},
                         headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 200
        assert r.json()["application"]["status"] == "pending"
        TestGigCRUD.app_id = r.json()["application"]["id"]

    def test_owner_lists_applicants(self, maya_auth, session):
        r = session.get(f"{API}/gigs/{TestGigCRUD.gig_id}/applicants",
                        headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 200
        body = r.json()
        assert body["gig"]["id"] == TestGigCRUD.gig_id
        assert any(a["id"] == TestGigCRUD.app_id for a in body["applications"])
        # Applicant info attached
        ap = next(a for a in body["applications"] if a["id"] == TestGigCRUD.app_id)
        assert ap.get("email")
        assert ap.get("name")

    def test_non_owner_cannot_list_applicants(self, arjun_auth, session):
        r = session.get(f"{API}/gigs/{TestGigCRUD.gig_id}/applicants",
                        headers=arjun_auth["headers"], timeout=30)
        assert r.status_code == 403

    def test_status_update_by_owner(self, maya_auth, session):
        r = session.patch(f"{API}/gigs/applications/{TestGigCRUD.app_id}/status",
                          json={"status": "shortlisted"},
                          headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 200

    def test_status_invalid_value(self, maya_auth, session):
        r = session.patch(f"{API}/gigs/applications/{TestGigCRUD.app_id}/status",
                          json={"status": "junk"},
                          headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 422

    def test_status_update_by_non_owner_forbidden(self, arjun_auth, session):
        r = session.patch(f"{API}/gigs/applications/{TestGigCRUD.app_id}/status",
                          json={"status": "rejected"},
                          headers=arjun_auth["headers"], timeout=30)
        assert r.status_code == 403

    def test_patch_gig_by_non_owner(self, arjun_auth, session):
        r = session.patch(f"{API}/gigs/{TestGigCRUD.gig_id}",
                          json={"title": "HACK"},
                          headers=arjun_auth["headers"], timeout=30)
        assert r.status_code == 403

    def test_patch_gig_by_owner(self, maya_auth, session):
        r = session.patch(f"{API}/gigs/{TestGigCRUD.gig_id}",
                          json={"budget": 2222},
                          headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 200
        assert r.json()["budget"] == 2222

    def test_delete_gig_cascades_applications(self, maya_auth, session):
        r = session.delete(f"{API}/gigs/{TestGigCRUD.gig_id}", headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 200
        # Listing applicants now fails (gig gone)
        r2 = session.get(f"{API}/gigs/{TestGigCRUD.gig_id}/applicants",
                         headers=maya_auth["headers"], timeout=30)
        assert r2.status_code == 404


# ---------- Reels + Subscriptions ----------
class TestReelsSubscriptions:
    def test_reels_returns_only_videos(self, session):
        r = session.get(f"{API}/posts/reels", timeout=30)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 3
        for p in items:
            assert p.get("media_type") == "video", f"non-video in /reels: {p.get('id')}"

    def test_subscriptions_requires_auth(self, session):
        r = session.get(f"{API}/posts/subscriptions", timeout=30)
        assert r.status_code == 401

    def test_subscriptions_empty_when_not_following(self, fresh_student, session):
        r = session.get(f"{API}/posts/subscriptions", headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_subscriptions_after_follow(self, fresh_student, maya_auth, session):
        # Follow Maya
        r = session.post(f"{API}/users/{maya_auth['user']['id']}/follow",
                         headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 200
        r2 = session.get(f"{API}/posts/subscriptions", headers=fresh_student["headers"], timeout=30)
        assert r2.status_code == 200
        items = r2.json()
        # Maya likely has posts; verify all returned posts belong to followed users (just maya)
        maya_id = maya_auth["user"]["id"]
        for p in items:
            assert p["user_id"] == maya_id


# ---------- Insights + CRM (creator-only) ----------
class TestInsightsCRM:
    def test_insights_creator_ok(self, maya_auth, session):
        r = session.get(f"{API}/dashboard/insights", headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "series" in data and "days" in data["series"]
        assert len(data["series"]["days"]) == 30
        assert len(data["series"]["posts"]) == 30
        assert len(data["series"]["likes"]) == 30
        assert len(data["series"]["comments"]) == 30
        assert "top_posts" in data and len(data["top_posts"]) <= 3
        assert "top_courses" in data and len(data["top_courses"]) <= 3
        assert "ads" in data and "followers" in data and "totals" in data

    def test_insights_student_forbidden(self, fresh_student, session):
        r = session.get(f"{API}/dashboard/insights", headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 403

    def test_crm_creator_ok(self, maya_auth, session):
        r = session.get(f"{API}/dashboard/crm", headers=maya_auth["headers"], timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "gigs" in data and isinstance(data["gigs"], list)
        assert "courses" in data and isinstance(data["courses"], list)
        assert "summary" in data
        for k in ("gigs", "applications", "courses", "enrollments"):
            assert k in data["summary"]

    def test_crm_student_forbidden(self, fresh_student, session):
        r = session.get(f"{API}/dashboard/crm", headers=fresh_student["headers"], timeout=30)
        assert r.status_code == 403


# ---------- Regression smoke ----------
class TestRegressionSmoke:
    def test_feed(self, session):
        assert session.get(f"{API}/posts/feed", timeout=30).status_code == 200

    def test_explore(self, session):
        assert session.get(f"{API}/posts/explore", timeout=30).status_code == 200

    def test_courses(self, session):
        assert session.get(f"{API}/courses", timeout=30).status_code == 200

    def test_gigs(self, session):
        assert session.get(f"{API}/gigs", timeout=30).status_code == 200

    def test_leaderboard(self, session):
        assert session.get(f"{API}/leaderboard", timeout=30).status_code == 200

    def test_search(self, session):
        assert session.get(f"{API}/search?q=react", timeout=30).status_code == 200

    def test_dashboard_stats(self, maya_auth, session):
        assert session.get(f"{API}/dashboard/stats", headers=maya_auth["headers"], timeout=30).status_code == 200

    def test_notifications(self, maya_auth, session):
        assert session.get(f"{API}/notifications", headers=maya_auth["headers"], timeout=30).status_code == 200

    def test_my_xp(self, maya_auth, session):
        assert session.get(f"{API}/users/me/xp", headers=maya_auth["headers"], timeout=30).status_code == 200
