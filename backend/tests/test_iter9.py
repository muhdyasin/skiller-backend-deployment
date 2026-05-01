"""Iteration 9 tests — Razorpay live (test mode) checkout + signature verify."""
import os
import hmac
import hashlib
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
RAZORPAY_KEY_SECRET = os.environ["RAZORPAY_KEY_SECRET"]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def maya_tok():
    return _login("maya@skiller.app", "Demo@123")


@pytest.fixture(scope="module")
def auth(maya_tok):
    return {"Authorization": f"Bearer {maya_tok}"}


class TestRazorpayCheckout:
    def test_order_created(self, auth):
        r = requests.post(f"{API}/billing/checkout", headers=auth,
                          json={"plan_id": "trial_active", "pay_with": "razorpay"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "order_created"
        assert d["provider"] == "razorpay"
        assert d["order_id"].startswith("order_")
        assert d["amount"] == 29900  # ₹299 in paise
        assert d["currency"] == "INR"
        assert d["key_id"] == os.environ["RAZORPAY_KEY_ID"]
        assert "plan_name" in d

    def test_invalid_signature_rejected(self, auth):
        r0 = requests.post(f"{API}/billing/checkout", headers=auth,
                           json={"plan_id": "trial_active", "pay_with": "razorpay"}, timeout=15)
        order_id = r0.json()["order_id"]
        r = requests.post(f"{API}/billing/verify-payment", headers=auth, json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_FAKE_BAD_SIG",
            "razorpay_signature": "deadbeef",
        }, timeout=15)
        assert r.status_code == 400
        assert "Invalid signature" in r.json()["detail"]

    def test_valid_signature_extends_premium(self, auth):
        # Capture before-state
        before = requests.get(f"{API}/billing/me", headers=auth, timeout=15).json()
        days_before = before["days_left"]

        r0 = requests.post(f"{API}/billing/checkout", headers=auth,
                           json={"plan_id": "trial_active", "pay_with": "razorpay"}, timeout=15)
        order_id = r0.json()["order_id"]

        payment_id = "pay_TEST_SIG_VERIFY"
        sig = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

        r = requests.post(f"{API}/billing/verify-payment", headers=auth, json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": sig,
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "paid"
        assert d["plan_id"] == "trial_active"

        after = requests.get(f"{API}/billing/me", headers=auth, timeout=15).json()
        assert after["plan"] == "pro"
        assert after["is_premium"] is True
        # Should have gained at least ~28 days (30d minus a sliver of clock drift)
        assert after["days_left"] >= days_before + 28

    def test_idempotent_already_paid(self, auth):
        # Re-verify the same order_id+payment_id should be idempotent
        r0 = requests.post(f"{API}/billing/checkout", headers=auth,
                           json={"plan_id": "trial_active", "pay_with": "razorpay"}, timeout=15)
        order_id = r0.json()["order_id"]
        payment_id = "pay_TEST_IDEMP"
        sig = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

        r1 = requests.post(f"{API}/billing/verify-payment", headers=auth, json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": sig,
        }, timeout=15)
        assert r1.status_code == 200
        assert r1.json()["status"] == "paid"

        r2 = requests.post(f"{API}/billing/verify-payment", headers=auth, json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": sig,
        }, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["status"] == "already_paid"

    def test_unknown_plan_rejected(self, auth):
        r = requests.post(f"{API}/billing/checkout", headers=auth,
                          json={"plan_id": "pro_yearly", "pay_with": "razorpay"}, timeout=15)
        # pro_yearly is `coming_soon` — not active
        assert r.status_code == 400

    def test_stripe_still_mock(self, auth):
        r = requests.post(f"{API}/billing/checkout", headers=auth,
                          json={"plan_id": "trial_active", "pay_with": "stripe"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "mock"
        assert d["provider"] == "stripe"

    def test_tokens_path_still_works(self):
        # Spin up a fresh user with no tokens and ensure the 'insufficient' guard
        import uuid
        tag = uuid.uuid4().hex[:8]
        email = f"rzp9_{tag}@skiller.app"
        reg = requests.post(f"{API}/auth/register", json={
            "email": email, "password": "Demo@123",
            "name": "Rzp Test", "username": f"rzp9{tag}",
        }, timeout=15)
        assert reg.status_code == 200
        tok = reg.json()["token"]
        r = requests.post(f"{API}/billing/checkout",
                          headers={"Authorization": f"Bearer {tok}"},
                          json={"plan_id": "trial_active", "pay_with": "tokens"}, timeout=15)
        assert r.status_code == 400
        assert "Insufficient" in r.json()["detail"]
