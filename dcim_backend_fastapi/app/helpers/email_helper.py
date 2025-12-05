"""
Email helper utilities for sending SMTP notifications from the DCIM backend.
"""
from email.message import EmailMessage
from typing import Iterable, List, Optional, Sequence
import smtplib

from app.core.config import settings
from app.core.logger import app_logger


def _normalize_recipients(recipients: Sequence[Optional[str]]) -> List[str]:
    """Filter out empty recipients and return a unique list."""
    seen = set()
    normalized: List[str] = []
    for recipient in recipients:
        if recipient and recipient not in seen:
            normalized.append(recipient)
            seen.add(recipient)
    return normalized


def send_email(
    subject: str,
    body: str,
    recipients: Sequence[Optional[str]],
) -> None:
    """
    Send a plain-text email via configured SMTP settings.

    Args:
        subject: Email subject line.
        body: Plain-text body.
        recipients: Iterable of recipient email addresses (duplicates/empties removed).
    """
    to_addresses = _normalize_recipients(recipients)
    if not to_addresses:
        app_logger.warning("Email send skipped because no recipients were provided.")
        return

    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        app_logger.warning("SMTP settings missing (host/from). Cannot send email.")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = ", ".join(to_addresses)
    message.set_content(body)

    try:
        if settings.SMTP_USE_SSL:
            smtp_class = smtplib.SMTP_SSL
        else:
            smtp_class = smtplib.SMTP

        with smtp_class(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT,
        ) as smtp:
            if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
                smtp.starttls()

            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            smtp.send_message(message)
            app_logger.info(
                "Sent email",
                extra={"subject": subject, "recipients": to_addresses},
            )
    except Exception:
        app_logger.exception("Failed to send email via SMTP")


def format_bulk_upload_report(
    job_id: str,
    summary: Optional[dict],
    results: Iterable[dict],
    failure_reason: Optional[str] = None,
) -> str:
    """
    Build a human-readable report body for a bulk upload job.
    """
    lines = [
        f"Bulk device upload job {job_id} has completed processing.",
    ]

    if failure_reason:
        lines.append("")
        lines.append("Status: FAILED")
        lines.append(f"Reason: {failure_reason}")
    elif summary:
        lines.append("")
        lines.append("Status: COMPLETED")
        lines.append(f"Entity: {summary.get('entity')}")
        lines.append(f"Total rows: {summary.get('total_rows')}")
        lines.append(f"Processed rows: {summary.get('processed')}")
        lines.append(f"Successful rows: {summary.get('success')}")
        lines.append(f"Failed rows: {summary.get('errors')}")
        if summary.get("aborted"):
            lines.append("Processing stopped early because skip_errors was disabled.")

    lines.append("")
    lines.append("Row results:")
    for row in results:
        status = row.get("status")
        row_no = row.get("row")
        if status == "success":
            data = row.get("data") or {}
            identifier = data.get("id") or data.get("device_id")
            lines.append(f"- Row {row_no}: SUCCESS (device_id={identifier})")
        elif status == "error":
            lines.append(f"- Row {row_no}: ERROR - {row.get('error')}")
        else:
            lines.append(f"- Row {row_no}: {status or 'UNKNOWN'}")

    return "\n".join(lines)


def send_bulk_upload_report(
    job_id: str,
    summary: Optional[dict],
    results: Iterable[dict],
    recipients: Sequence[Optional[str]],
    failure_reason: Optional[str] = None,
) -> None:
    """
    Format and send the standard bulk upload report email.
    """
    print(f"Sending bulk upload report for job {job_id}")
    print(f"Summary: {summary}")
    print(f"Results: {results}")
    print(f"Recipients: {recipients}")
    print(f"Failure reason: {failure_reason}")
    
    # subject = f"DCIM Bulk Device Upload Report | Job {job_id}"
    # body = format_bulk_upload_report(
    #     job_id=job_id,
    #     summary=summary,
    #     results=results,
    #     failure_reason=failure_reason,
    # )
    # send_email(subject=subject, body=body, recipients=recipients)

