"""Skiller iteration-3 backend tests.

Covers:
- WebSocket /api/ws auth (valid + invalid token, connected event, real-time notification)
- POST /api/posts media URL allowlist (data:/javascript:/empty rejected, https/http/api/files accepted)
- POST /api/auth/forgot-password (no enumeration; logs PASSWORD_RESET_LINK)
- POST /api/auth/reset-password (invalid/expired/replay/valid + login with new pw + restore)
"""
import os, re, asyncio, json, time, uuid, subprocess
import pytest, requests
import websockets

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE}/api"
WS_URL = BASE.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws"

MAYA = {"email": "maya@skiller.app", "password": "Demo@123"}
ARJUN = {"email": "arjun@skiller.app", "password": "Demo@123"}
NEHA = {"email": "neha@skiller.app", "password": "Demo@123"}


def hdr(t): return {"Authorization": f"Bearer {t}"}


def login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="module")
def maya():
    t, u = login(MAYA); return {"token": t, "user": u}


@pytest.fixture(scope="module")
def arjun():
    t, u = login(ARJUN); return {"token": t, "user": u}


# ---------- WEBSOCKET ----------
class TestWebSocket:
    def test_invalid_token_closes(self):
        async def run():
            try:
                async with websockets.connect(f"{WS_URL}?token=invalid.jwt.here") as ws:
                    # Should close immediately. Try recv -> ConnectionClosed
                    await asyncio.wait_for(ws.recv(), timeout=5)
                    return None
            except websockets.ConnectionClosed as e:
                return e.code
            except Exception as e:
                return f"err:{e}"
        code = asyncio.run(run())
        # Server closes BEFORE accept() so client sees HTTP 403 rejection (acceptable).
        # If server were to accept() then close(4401), code would be 4401. Accept either.
        ok = code == 4401 or (isinstance(code, str) and ("403" in code or "rejected" in code))
        assert ok, f"expected invalid-token rejection, got {code}"

    def test_valid_token_connected_event(self, maya):
        async def run():
            async with websockets.connect(f"{WS_URL}?token={maya['token']}") as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                return json.loads(msg)
        d = asyncio.run(run())
        assert d.get("type") == "connected"
        assert d.get("user_id") == maya["user"]["id"]

    def test_realtime_notification_on_follow(self, maya, arjun):
        """Arjun connects; Maya follows Arjun; Arjun should receive a notification event."""
        async def run():
            async with websockets.connect(f"{WS_URL}?token={arjun['token']}") as ws:
                # Drain 'connected'
                await asyncio.wait_for(ws.recv(), timeout=5)
                # Maya follows arjun (toggle - ensure 'following' true; if already, unfollow then follow)
                arjun_id = arjun["user"]["id"]
                state = requests.get(f"{API}/users/arjun", headers=hdr(maya["token"]), timeout=10).json()
                if state.get("is_following"):
                    requests.post(f"{API}/users/{arjun_id}/follow", headers=hdr(maya["token"]), timeout=10)
                # follow now
                r = requests.post(f"{API}/users/{arjun_id}/follow", headers=hdr(maya["token"]), timeout=10)
                assert r.status_code == 200 and r.json()["following"] is True
                # Receive notification
                evt = None
                for _ in range(5):
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5)
                        d = json.loads(raw)
                        if d.get("type") == "notification":
                            evt = d; break
                    except asyncio.TimeoutError:
                        break
                # cleanup follow
                requests.post(f"{API}/users/{arjun_id}/follow", headers=hdr(maya["token"]), timeout=10)
                return evt
        evt = asyncio.run(run())
        assert evt is not None, "did not receive WS notification"
        assert evt["type"] == "notification"
        assert "data" in evt


# ---------- MEDIA URL VALIDATION ----------
class TestMediaValidation:
    @pytest.mark.parametrize("media", [
        "data:image/png;base64,iVBORw0KGgo=",
        "javascript:alert(1)",
        "",
        "ftp://example.com/x.png",
        "file:///etc/passwd",
        "blob:abc",
    ])
    def test_reject_invalid_media(self, maya, media):
        r = requests.post(f"{API}/posts", headers=hdr(maya["token"]),
                          json={"caption": "TEST_iter3", "media": media, "media_type": "image"}, timeout=10)
        assert r.status_code == 422, f"expected 422 for media={media!r}, got {r.status_code} {r.text}"

    @pytest.mark.parametrize("media", [
        "https://images.unsplash.com/photo-x.jpg",
        "http://example.com/x.png",
        "/api/files/uploads/abc.png",
    ])
    def test_accept_valid_media(self, maya, media):
        r = requests.post(f"{API}/posts", headers=hdr(maya["token"]),
                          json={"caption": "TEST_iter3", "media": media, "media_type": "image"}, timeout=10)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        # cleanup
        requests.delete(f"{API}/posts/{pid}", headers=hdr(maya["token"]), timeout=10)


# ---------- FORGOT/RESET PASSWORD ----------
def tail_log_for_token(email, since_ts, attempts=8, sleep=0.5):
    """Tail backend log for PASSWORD_RESET_LINK matching email; return token."""
    pat = re.compile(r"PASSWORD_RESET_LINK for " + re.escape(email) + r": (\S+)")
    for _ in range(attempts):
        try:
            out = subprocess.check_output(
                ["tail", "-n", "500", "/var/log/supervisor/backend.err.log"],
                stderr=subprocess.DEVNULL, timeout=5,
            ).decode(errors="ignore")
        except Exception:
            out = ""
        for line in out.splitlines()[::-1]:
            m = pat.search(line)
            if m:
                link = m.group(1)
                # token is last path segment
                return link.rstrip("/").rsplit("/", 1)[-1]
        time.sleep(sleep)
    return None


class TestPasswordReset:
    def test_forgot_unknown_email_returns_200(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": f"nobody_{uuid.uuid4().hex[:6]}@skiller.app"}, timeout=10)
        assert r.status_code == 200
        assert "message" in r.json()

    def test_forgot_known_email_returns_200_and_logs_link(self):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": NEHA["email"]}, timeout=10)
        assert r.status_code == 200
        # message identical regardless (no enumeration)
        assert "exists" in r.json()["message"].lower() or "reset" in r.json()["message"].lower()
        token = tail_log_for_token(NEHA["email"], time.time())
        assert token, "PASSWORD_RESET_LINK not found in backend log"
        assert len(token) > 20

    def test_reset_invalid_token(self):
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": "bogus_token_xyz", "new_password": "NewPass@123"}, timeout=10)
        assert r.status_code == 400
        assert "invalid" in r.json()["detail"].lower() or "expired" in r.json()["detail"].lower()

    def test_reset_valid_token_then_replay_blocked_then_restore(self):
        # Trigger forgot for NEHA
        r = requests.post(f"{API}/auth/forgot-password", json={"email": NEHA["email"]}, timeout=10)
        assert r.status_code == 200
        token = tail_log_for_token(NEHA["email"], time.time())
        assert token, "no token in logs"
        new_pw = "Reset@" + uuid.uuid4().hex[:6]
        # reset
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": token, "new_password": new_pw}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True
        # old password should fail
        r = requests.post(f"{API}/auth/login", json={"email": NEHA["email"], "password": "Demo@123"}, timeout=10)
        assert r.status_code == 401
        # new password should work
        r = requests.post(f"{API}/auth/login", json={"email": NEHA["email"], "password": new_pw}, timeout=10)
        assert r.status_code == 200
        # replay token should fail
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": token, "new_password": "AnotherPw@1"}, timeout=10)
        assert r.status_code == 400
        # ----- restore Neha's password to Demo@123 -----
        r = requests.post(f"{API}/auth/forgot-password", json={"email": NEHA["email"]}, timeout=10)
        assert r.status_code == 200
        restore_token = tail_log_for_token(NEHA["email"], time.time())
        assert restore_token, "no restore token"
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": restore_token, "new_password": "Demo@123"}, timeout=10)
        assert r.status_code == 200
        # confirm
        r = requests.post(f"{API}/auth/login", json=NEHA, timeout=10)
        assert r.status_code == 200, "FAILED to restore Neha password to Demo@123"
