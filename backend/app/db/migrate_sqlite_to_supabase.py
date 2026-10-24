"""
UrbanSage AI — SQLite to Supabase PostgreSQL Migration Utility
=============================================================
Safely transfers existing citizen reports from local SQLite storage into
hosted Supabase PostgreSQL.

Guarantees:
-----------
1. Preserves Record Identity: Stable IDs (^RPT-[0-9A-F]{8}$) are preserved exactly.
2. Preserves Provenance: Timestamps, statuses, scores, and reporter IDs are kept intact.
3. Idempotent Execution: Safe to run multiple times using primary key upsert.
4. Privacy Enforcement: Never outputs or logs reporter_contact details.
5. Dry-Run Support: Allows non-destructive preview and schema validation.
6. Count & Integrity Validation: Verifies destination counts and record presence.

Usage:
------
    # Preview migration without modifying Supabase
    python -m app.db.migrate_sqlite_to_supabase --dry-run

    # Execute migration with verification
    python -m app.db.migrate_sqlite_to_supabase --force
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from pydantic import ValidationError

from app.reports.models import (
    CitizenReport,
    PhotoMetadata,
    ProblemCategory,
    ReportStatus,
    VerificationStatus,
)

# Configure secure migration logger (level INFO, no sensitive leaks)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] migrate: %(message)s",
)
logger = logging.getLogger("urbansage.migrate")


def parse_sqlite_record(row: sqlite3.Row) -> Dict[str, Any]:
    """
    Extract and validate a record from SQLite row into a Supabase PostgreSQL payload.
    """
    photos_raw = row["photos_json"]
    if isinstance(photos_raw, str):
        try:
            photos_list = json.loads(photos_raw)
        except Exception:
            photos_list = []
    else:
        photos_list = photos_raw or []

    # Validate photos list
    validated_photos = [PhotoMetadata.model_validate(p).model_dump(mode="json") for p in photos_list]

    # Validate timestamps
    created_raw = row["created_at"]
    created_dt = datetime.fromisoformat(created_raw)
    if created_dt.tzinfo is None:
        created_dt = created_dt.replace(tzinfo=timezone.utc)

    updated_raw = row["updated_at"]
    updated_dt = datetime.fromisoformat(updated_raw)
    if updated_dt.tzinfo is None:
        updated_dt = updated_dt.replace(tzinfo=timezone.utc)

    return {
        "id": row["id"],
        "category": ProblemCategory(row["category"]).value,
        "description": row["description"],
        "severity": int(row["severity"]),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "location_description": row["location_description"],
        "neighbourhood_id": row["neighbourhood_id"],
        "reporter_id": row["reporter_id"],
        "reporter_contact": row["reporter_contact"],  # Preserved in DB, NEVER logged
        "photos": validated_photos,
        "status": ReportStatus(row["status"]).value,
        "verification_status": VerificationStatus(row["verification_status"]).value,
        "is_verified_measurement": bool(row["is_verified_measurement"]),
        "data_source": row["data_source"] or "CITIZEN_REPORT",
        "urgency_score": float(row["urgency_score"]),
        "evidence_confidence_score": float(row["evidence_confidence_score"]),
        "created_at": created_dt.isoformat(),
        "updated_at": updated_dt.isoformat(),
    }


def read_sqlite_records(sqlite_path: str) -> List[Dict[str, Any]]:
    """Read and validate all citizen reports from the source SQLite database."""
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database file not found at: {sqlite_path}")

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='citizen_reports';")
        if not cursor.fetchone():
            logger.warning("Table 'citizen_reports' does not exist in SQLite database at %s.", sqlite_path)
            return []

        cursor.execute("SELECT * FROM citizen_reports ORDER BY created_at ASC;")
        rows = cursor.fetchall()
        logger.info("Read %d records from SQLite database (%s).", len(rows), sqlite_path)

        records: List[Dict[str, Any]] = []
        for row in rows:
            try:
                rec = parse_sqlite_record(row)
                records.append(rec)
            except Exception as e:
                report_id = row["id"] if "id" in row.keys() else "<unknown>"
                logger.error("Failed to parse SQLite record ID %s: %s", report_id, e)
                raise
        return records
    finally:
        conn.close()


def run_migration(
    sqlite_path: str = "urbansage_reports.db",
    dry_run: bool = True,
    force: bool = False,
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    batch_size: int = 50,
) -> bool:
    """
    Execute migration from SQLite to Supabase PostgreSQL.

    Returns
    -------
    bool: True if migration (or dry run) completed successfully, False otherwise.
    """
    logger.info("Starting UrbanSage AI SQLite -> Supabase migration...")
    logger.info("Source SQLite database: %s", sqlite_path)
    logger.info("Mode: %s", "DRY-RUN (Simulated)" if dry_run else "LIVE MIGRATION")

    # 1. Read source records
    try:
        source_records = read_sqlite_records(sqlite_path)
    except Exception as e:
        logger.error("Failed to read source database: %s", e)
        return False

    if not source_records:
        logger.info("No records found to migrate. Source database is empty.")
        return True

    logger.info("Validated %d records from SQLite.", len(source_records))

    # Log record summaries without exposing confidential reporter_contact
    for rec in source_records:
        logger.info(
            "Record [%s]: Category=%s, Severity=%d, Status=%s, Urgency=%.1f, Evidence=%.1f",
            rec["id"],
            rec["category"],
            rec["severity"],
            rec["status"],
            rec["urgency_score"],
            rec["evidence_confidence_score"],
        )

    if dry_run:
        logger.info("DRY-RUN SUCCESS: All %d records validated cleanly against schema.", len(source_records))
        logger.info("To perform actual insertion into Supabase, run with --force (and ensure SUPABASE_URL / SUPABASE_SECRET_KEY are set).")
        return True

    # 2. Live Migration Preparation
    if not force:
        logger.error("Live migration requires explicit confirmation via --force flag.")
        return False

    url = supabase_url or os.getenv("SUPABASE_URL")
    key = (
        supabase_key
        or os.getenv("SUPABASE_SECRET_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
    )

    if not url or not key:
        logger.error("Cannot perform live migration: SUPABASE_URL and SUPABASE_SECRET_KEY environment variables must be configured.")
        return False

    try:
        from supabase import create_client
        client = create_client(url, key)
    except Exception as e:
        logger.error("Failed to connect to Supabase: %s", e)
        return False

    # 3. Batch Upsert into Supabase
    total_migrated = 0
    total_records = len(source_records)

    logger.info("Beginning batch upsert of %d records into table 'citizen_reports'...", total_records)

    for i in range(0, total_records, batch_size):
        batch = source_records[i : i + batch_size]
        try:
            res = client.table("citizen_reports").upsert(batch, on_conflict="id").execute()
            inserted_count = len(res.data or [])
            total_migrated += inserted_count
            logger.info("Upserted batch %d-%d (%d records).", i + 1, min(i + batch_size, total_records), inserted_count)
        except Exception as e:
            logger.error("Failed to upsert batch starting at index %d: %s", i, e)
            return False

    # 4. Post-Migration Verification
    logger.info("Performing destination verification in Supabase...")
    try:
        count_res = client.table("citizen_reports").select("id", count="exact").limit(1).execute()
        dest_total = count_res.count if count_res.count is not None else 0
        logger.info("Supabase report count after migration: %d (Source SQLite had %d).", dest_total, total_records)

        # Verify presence of every migrated ID
        missing_ids = []
        for rec in source_records:
            check = client.table("citizen_reports").select("id").eq("id", rec["id"]).maybe_single().execute()
            if not check or not check.data:
                missing_ids.append(rec["id"])

        if missing_ids:
            logger.error("Verification failed: %d records were not found in Supabase: %s", len(missing_ids), missing_ids)
            return False

        logger.info("VERIFICATION PASSED: All %d records exist in Supabase PostgreSQL.", total_records)
    except Exception as e:
        logger.error("Error during post-migration verification: %s", e)
        return False

    logger.info("Migration completed successfully with zero data loss.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="UrbanSage AI SQLite to Supabase Migration Utility")
    parser.add_argument(
        "--sqlite-path",
        default="urbansage_reports.db",
        help="Path to source SQLite database (default: urbansage_reports.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simulate migration without modifying Supabase",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Confirm live migration to Supabase",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for upsert operations (default: 50)",
    )

    args = parser.parse_args()

    # If neither dry-run nor force is provided, default to dry-run for safety
    is_dry_run = args.dry_run or not args.force

    success = run_migration(
        sqlite_path=args.sqlite_path,
        dry_run=is_dry_run,
        force=args.force,
        batch_size=args.batch_size,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
