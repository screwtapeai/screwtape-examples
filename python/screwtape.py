"""Minimal client for the public Screwtape.ai API. Standard library only.

Docs: https://screwtape.ai/docs/   Spec: https://screwtape.ai/openapi.json
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_URL = os.environ.get("SCREWTAPE_API_URL", "https://screwtape.ai")
USER_AGENT = "screwtape-examples/1.0"


class ScrewtapeError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("SCREWTAPE_API_KEY")
    if not key:
        raise ScrewtapeError("Set SCREWTAPE_API_KEY. Free key: https://screwtape.ai/signup/")
    return key


def _post(path: str, body: dict, idempotency_key: str | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = urllib.request.Request(f"{API_URL}{path}", data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise ScrewtapeError(f"HTTP {error.code}: {error.read().decode()[:400]}") from None


def invoice_checks(invoice: dict) -> list[dict]:
    """Required fields, plus: line items + tax must add up to the total."""
    parts = [f"items.{i}.amount" for i in range(len(invoice.get("items") or []))] + ["tax"]
    return [
        {"type": "required_fields", "paths": ["invoice_id", "vendor", "total", "currency"]},
        {"type": "sum", "parts": parts, "total": "total", "tolerance": 0.01},
    ]


def duplicate_check(store: bool = True, retain_days: int = 180) -> dict:
    """Compare this invoice with the invoices your API key recorded earlier."""
    return {
        "vendor_path": "vendor",
        "invoice_id_path": "invoice_id",
        "amount_path": "total",
        "currency_path": "currency",
        "date_path": "date",
        "store": store,
        "retain_days": retain_days,
    }


def check_payment(invoice: dict, evidence: list[str], task: str | None = None, idempotency_key: str | None = None) -> dict:
    """Spend check: duplicate check + invoice math + a verdict against your evidence (PO, contract, email).

    Pay only when result["next_step"]["action"] == "pass".
    """
    body = {
        "task": task or f"Decide whether the agent may pay invoice {invoice.get('invoice_id')} from {invoice.get('vendor')}.",
        "agent_output": json.dumps(invoice),
        "evidence": evidence,
        "checks": invoice_checks(invoice),
        "duplicate": duplicate_check(),
    }
    return _post("/v1/duplicate", body, idempotency_key)


def judge(task: str, agent_output: str, evidence: list[str] | None = None, checks: list[dict] | None = None) -> dict:
    """Verdict (pass, fail or retry) on any agent output before it is acted on."""
    body: dict = {"task": task, "agent_output": agent_output}
    if evidence:
        body["evidence"] = evidence
    if checks:
        body["checks"] = checks
    return _post("/v1/judge", body)


def may_pay(result: dict) -> bool:
    return (result.get("next_step") or {}).get("action") == "pass"


def summary(result: dict) -> str:
    step = result.get("next_step") or {}
    dup = (result.get("duplicate") or {}).get("status", "n/a")
    receipt = (result.get("receipt") or {}).get("receipt_id", "none")
    return f"verdict={result.get('verdict')} action={step.get('action')} reason={step.get('error_type')} duplicate={dup} receipt={receipt}"
