"""
UrbanSage AI — Controlled User Provisioning Script
==================================================
Provisions verified municipal administrator, infrastructure partner,
and demonstration citizen accounts directly into Supabase Auth with trusted app_metadata.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load backend environment variables
backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(backend_dir / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in backend/.env")
    sys.exit(1)

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

ACCOUNTS_TO_PROVISION = [
    {
        "email": "admin@urbansage.gov.in",
        "password": os.getenv("PROVISION_ADMIN_PASSWORD", "AdminSecure2026!"),
        "role": "administrator",
        "user_metadata": {
            "full_name": "Municipal Chief Commissioner",
            "department": "BBMP Municipal Control Room",
        },
        "app_metadata": {
            "role": "administrator",
            "department": "BBMP Municipal Control Room",
        },
    },
    {
        "email": "partner@bbmp-works.in",
        "password": os.getenv("PROVISION_PARTNER_PASSWORD", "PartnerSecure2026!"),
        "role": "contractor",
        "user_metadata": {
            "full_name": "Er. K. Ramesh (Works Supervisor)",
            "vendor_id": "VND-BBMP-WORKS-01",
            "vendor_name": "Bengaluru Urban Drainage & Infra Ltd",
        },
        "app_metadata": {
            "role": "contractor",
            "vendor_id": "VND-BBMP-WORKS-01",
            "vendor_name": "Bengaluru Urban Drainage & Infra Ltd",
        },
    },
    {
        "email": "citizen@urbansage.in",
        "password": os.getenv("PROVISION_CITIZEN_PASSWORD", "CitizenSecure2026!"),
        "role": "citizen",
        "user_metadata": {
            "full_name": "Ananya Sharma (Citizen Reporter)",
            "neighbourhood_id": "NBR-001",
        },
        "app_metadata": {
            "role": "citizen",
        },
    },
]


def provision_accounts():
    print(f"Connecting to Supabase Auth at {SUPABASE_URL}...")
    existing_users = client.auth.admin.list_users()
    existing_by_email = {u.email.lower(): u for u in existing_users if u.email}
    print(f"Found {len(existing_by_email)} existing user(s) in Supabase Auth.")

    for acc in ACCOUNTS_TO_PROVISION:
        email = acc["email"].lower()
        if email in existing_by_email:
            user = existing_by_email[email]
            print(f"User {email} exists (ID: {user.id}). Updating app_metadata and password...")
            client.auth.admin.update_user_by_id(
                user.id,
                {
                    "password": acc["password"],
                    "email_confirm": True,
                    "app_metadata": acc["app_metadata"],
                    "user_metadata": acc["user_metadata"],
                },
            )
            print(f"Updated {email} successfully.")
        else:
            print(f"Creating user {email} ({acc['role']})...")
            created = client.auth.admin.create_user(
                {
                    "email": email,
                    "password": acc["password"],
                    "email_confirm": True,
                    "app_metadata": acc["app_metadata"],
                    "user_metadata": acc["user_metadata"],
                }
            )
            print(f"Created {email} successfully (ID: {created.user.id}).")

    print("\n--- Summary of Provisioned Accounts ---")
    users = client.auth.admin.list_users()
    for u in users:
        role = u.app_metadata.get("role", "citizen")
        print(f"Email: {u.email} | Role: {role} | Confirmed: {bool(u.email_confirmed_at)} | ID: {u.id}")


if __name__ == "__main__":
    provision_accounts()
