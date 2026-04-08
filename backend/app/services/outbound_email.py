from __future__ import annotations

import asyncio
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

from app.core.config import settings


def outbound_email_enabled() -> bool:
    return bool(
        settings.outbound_email_enabled
        and settings.smtp_host
        and settings.outbound_email_from
    )


def _send_email_batch_sync(*, subject: str, body: str, recipients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not settings.outbound_email_enabled:
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "skipped",
                "error": "Outbound email is disabled",
                "sent_at": None,
            }
            for recipient in recipients
        ]

    if not settings.smtp_host or not settings.outbound_email_from:
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "skipped",
                "error": "SMTP is not configured",
                "sent_at": None,
            }
            for recipient in recipients
        ]

    prepared = []
    for recipient in recipients:
        email = str(recipient.get("email") or "").strip()
        if not email:
            prepared.append(
                {
                    "user_id": recipient.get("user_id"),
                    "email": email,
                    "status": "skipped",
                    "error": "Recipient has no email address",
                    "sent_at": None,
                }
            )
        else:
            prepared.append({**recipient, "email": email})

    smtp_client = None
    try:
        if settings.smtp_use_ssl:
            smtp_client = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20)
        else:
            smtp_client = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
            if settings.smtp_use_tls:
                smtp_client.starttls()
        if settings.smtp_username:
            smtp_client.login(settings.smtp_username, settings.smtp_password)
    except Exception as exc:
        if smtp_client is not None:
            try:
                smtp_client.quit()
            except Exception:
                pass
        error = str(exc)[:500]
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "failed" if recipient.get("email") else recipient.get("status", "skipped"),
                "error": error if recipient.get("email") else recipient.get("error"),
                "sent_at": None,
            }
            for recipient in prepared
        ]

    results: list[dict[str, Any]] = []
    try:
        for recipient in prepared:
            email = str(recipient.get("email") or "").strip()
            if not email or recipient.get("status") == "skipped":
                results.append(
                    {
                        "user_id": recipient.get("user_id"),
                        "email": email,
                        "status": recipient.get("status", "skipped"),
                        "error": recipient.get("error"),
                        "sent_at": None,
                    }
                )
                continue

            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = formataddr((settings.outbound_email_from_name, settings.outbound_email_from))
            message["To"] = email
            if settings.outbound_email_reply_to:
                message["Reply-To"] = settings.outbound_email_reply_to
            message.set_content(body)

            try:
                smtp_client.send_message(message)
                results.append(
                    {
                        "user_id": recipient.get("user_id"),
                        "email": email,
                        "status": "sent",
                        "error": None,
                        "sent_at": datetime.now(timezone.utc),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "user_id": recipient.get("user_id"),
                        "email": email,
                        "status": "failed",
                        "error": str(exc)[:500],
                        "sent_at": None,
                    }
                )
    finally:
        try:
            smtp_client.quit()
        except Exception:
            pass

    return results


async def send_outbound_email_batch(*, subject: str, body: str, recipients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not recipients:
        return []
    return await asyncio.to_thread(_send_email_batch_sync, subject=subject, body=body, recipients=recipients)
