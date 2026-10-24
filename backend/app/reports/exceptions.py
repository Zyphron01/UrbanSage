"""
UrbanSage AI — Citizen Reporting Domain Exceptions
===================================================
Domain-specific exceptions for citizen environmental reporting and persistence.
"""

from __future__ import annotations


class ReportError(Exception):
    """Base exception for all citizen reporting operations."""


class ReportNotFoundError(ReportError):
    """Raised when a requested citizen report ID does not exist."""

    def __init__(self, report_id: str):
        self.report_id = report_id
        super().__init__(f"Citizen report not found: {report_id}")


class ReportValidationError(ReportError):
    """Raised when a citizen report payload violates domain rules before persistence."""


class DuplicateReportError(ReportError):
    """Raised when an identical or spammed report from the same reporter is rejected."""

    def __init__(self, message: str = "Duplicate report detected within throttle window"):
        super().__init__(message)


class ReportPersistenceError(ReportError):
    """Raised when a database I/O or SQLite constraint failure occurs."""


class InvalidStatusTransitionError(ReportValidationError):
    """Raised when an illegal status transition is requested."""

    def __init__(self, from_status: str, to_status: str, reason: str = ""):
        self.from_status = from_status
        self.to_status = to_status
        msg = f"Cannot transition report from status '{from_status}' to '{to_status}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)
