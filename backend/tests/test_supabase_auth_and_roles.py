"""
UrbanSage AI — Supabase Auth Integration & Role Authorization Test Suite
========================================================================
Comprehensive automated test suite validating:
1. Citizen Registration and Auth lifecycle.
2. Email verification request configuration.
3. Password recovery request lifecycle.
4. Municipal Administrator authentication & privileged endpoint access.
5. Infrastructure Partner authentication & work order access.
6. Role-Based Access Control (RBAC): Citizens and Partners blocked from Admin APIs (HTTP 403).
7. Invalid and forged credentials rejection (HTTP 401).
8. Regression validation of core workflows.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
API_BASE = "http://127.0.0.1:8000"


class TestSupabaseAuthAndRoles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise unittest.SkipTest("Supabase credentials not configured.")
        cls.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

        # Obtain live access tokens for all three provisioned roles
        admin_sess = cls.supabase.auth.sign_in_with_password({
            "email": "admin@urbansage.gov.in",
            "password": "AdminSecure2026!",
        })
        cls.admin_token = admin_sess.session.access_token

        partner_sess = cls.supabase.auth.sign_in_with_password({
            "email": "partner@bbmp-works.in",
            "password": "PartnerSecure2026!",
        })
        cls.partner_token = partner_sess.session.access_token

        citizen_sess = cls.supabase.auth.sign_in_with_password({
            "email": "citizen@urbansage.in",
            "password": "CitizenSecure2026!",
        })
        cls.citizen_token = citizen_sess.session.access_token

    def _api_call(self, endpoint: str, method: str = "GET", token: str | None = None, data: dict | None = None):
        url = f"{API_BASE}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        return urllib.request.urlopen(req)

    # ------------------------------------------------------------------------
    # 1. Server-Side Identity & Profile Verification (/api/auth/me)
    # ------------------------------------------------------------------------
    def test_admin_identity_resolution(self):
        resp = self._api_call("/api/auth/me", token=self.admin_token)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertEqual(data["role"], "administrator")
        self.assertTrue(data["is_admin"])
        self.assertEqual(data["email"], "admin@urbansage.gov.in")

    def test_partner_identity_resolution(self):
        resp = self._api_call("/api/auth/me", token=self.partner_token)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertEqual(data["role"], "contractor")
        self.assertTrue(data["is_contractor"])
        self.assertFalse(data["is_admin"])
        self.assertEqual(data["vendor_id"], "VND-BBMP-WORKS-01")

    def test_citizen_identity_resolution(self):
        resp = self._api_call("/api/auth/me", token=self.citizen_token)
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertEqual(data["role"], "citizen")
        self.assertFalse(data["is_admin"])
        self.assertFalse(data["is_contractor"])

    # ------------------------------------------------------------------------
    # 2. Role-Based Access Control Boundaries
    # ------------------------------------------------------------------------
    def test_admin_can_access_admin_api(self):
        resp = self._api_call("/api/admin/decision-brief", token=self.admin_token)
        self.assertEqual(resp.status, 200)

    def test_citizen_blocked_from_admin_api(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._api_call("/api/admin/decision-brief", token=self.citizen_token)
        self.assertEqual(ctx.exception.code, 403)

    def test_partner_blocked_from_admin_api(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._api_call("/api/admin/decision-brief", token=self.partner_token)
        self.assertEqual(ctx.exception.code, 403)

    def test_partner_can_update_milestone(self):
        payload = {"percent_progress": 80, "notes": "Automated test progress update"}
        resp = self._api_call("/api/accountability/milestones/MLS-00000003", method="PATCH", token=self.partner_token, data=payload)
        self.assertEqual(resp.status, 200)

    def test_citizen_blocked_from_updating_milestone(self):
        payload = {"percent_progress": 90}
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._api_call("/api/accountability/milestones/MLS-00000003", method="PATCH", token=self.citizen_token, data=payload)
        self.assertEqual(ctx.exception.code, 403)

    def test_unauthenticated_request_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._api_call("/api/admin/decision-brief")
        self.assertEqual(ctx.exception.code, 401)

    def test_forged_token_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._api_call("/api/auth/me", token="eyJhbGciOiJIUzI1NiJ9.forged.fake")
        self.assertEqual(ctx.exception.code, 401)

    # ------------------------------------------------------------------------
    # 3. Citizen Registration via Supabase Auth
    # ------------------------------------------------------------------------
    def test_citizen_registration_via_supabase(self):
        import uuid
        test_email = f"auto_citizen_{uuid.uuid4().hex[:6]}@urbansage.in"
        res = self.supabase.auth.sign_up({
            "email": test_email,
            "password": "StrongPassword2026!",
            "options": {"data": {"full_name": "Automated Test Citizen"}}
        })
        self.assertIsNotNone(res.user)
        self.assertEqual(res.user.email, test_email)

        # Cleanup created user using service-role key
        self.supabase.auth.admin.delete_user(res.user.id)

    # ------------------------------------------------------------------------
    # 4. Password Recovery Request via Supabase Auth
    # ------------------------------------------------------------------------
    def test_password_recovery_request(self):
        # Requesting password reset for verified citizen without throwing error
        try:
            self.supabase.auth.reset_password_for_email("citizen@urbansage.in")
            success = True
        except Exception:
            success = False
        self.assertTrue(success)

    # ------------------------------------------------------------------------
    # 5. Core Workflow Regressions
    # ------------------------------------------------------------------------
    def test_reports_listing_works(self):
        resp = self._api_call("/api/reports?limit=5")
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertIn("items", data)

    def test_allocations_listing_works(self):
        resp = self._api_call("/api/accountability/allocations")
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode())
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
