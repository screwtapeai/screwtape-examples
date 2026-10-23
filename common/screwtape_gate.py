"""Tiny client for the public Screwtape.ai API (https://screwtape.ai/docs/).

Shared by crewai/, langgraph/ and autogen/. Standard library only.
Fields used here come from https://screwtape.ai/openapi.json (v1.1.0).
"""
import json, os, urllib.request, urllib.error

API = os.environ.get("SCREWTAPE_API_URL", "https://screwtape.ai")
UA = "screwtape-examples/0.2"


def _key() -> str:
    key = os.environ.get("SCREWTAPE_API_KEY")
    if not key:
        raise SystemExit("Set SCREWTAPE_API_KEY (free key: https://screwtape.ai/signup/)")
    return key


def _request(method: str, path: str, body=None, headers=None, raw=False):
    h = {"Authorization": f"Bearer {_key()}", "User-Agent": UA}
    if body is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(f"{API}{path}", method=method, headers=h,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read().decode()
            return data if raw else json.loads(data)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:500]}")


# ---------- checks ----------

def invoice_checks(decision: dict) -> list:
    """required_fields + sum, built from however many line items the invoice has."""
    n = len(decision.get("items") or [])
    return [
        {"type": "required_fields",
         "paths": ["invoice_id", "vendor", "subtotal", "tax", "total", "decision"]},
        # items.0.amount + ... + items.N-1.amount + tax must equal total (max 20 parts)
        {"type": "sum", "parts": [f"items.{i}.amount" for i in range(n)] + ["tax"],
         "total": "total", "tolerance": 0.01},
    ]


def duplicate_check(store: bool = True, window_days: int = 3, retain_days: int = 180) -> dict:
    """Duplicate-invoice check (Bearer key only, at most one per call).

    Compares this invoice with ones the same key recorded earlier. Screwtape keeps
    keyed HMAC fingerprints only, and only when store is true (default false in the
    API). retain_days defaults to 180 (1 to 400). date_path enables the
    same-vendor/amount/date rule within window_days (0 to 30, default 3).
    Fingerprints are recorded only when the overall verdict is not fail
    (see duplicate.stored in the response).
    """
    return {"type": "duplicate", "vendor_path": "vendor", "invoice_id_path": "invoice_id",
            "amount_path": "total", "currency_path": "currency", "date_path": "invoice_date",
            "window_days": window_days, "store": store, "retain_days": retain_days}


# ---------- judge ----------

def judge_invoice_decision(decision: dict, invoice_text: str, *, duplicate: bool = False,
                           store: bool = True, advisory: bool = False,
                           idempotency_key: str | None = None) -> dict:
    """POST /v1/judge with the invoice checks.

    duplicate=True adds the duplicate check. advisory=True sends mode "advisory":
    same verdict and receipt, plus decision_owner "human", recommended_action
    (approve | review | return) and a notice. idempotency_key (8-128 chars of
    letters, digits, _ or -) makes a retry of the same invoice report
    duplicate.status "replay" instead of "duplicate".
    """
    checks = invoice_checks(decision) + ([duplicate_check(store=store)] if duplicate else [])
    body = {
        "task": "Decide whether to approve and pay this invoice. Return JSON.",
        "agent_output": json.dumps(decision),
        "evidence": [invoice_text],   # without evidence the model cannot ground the answer
        "checks": checks,
        "agent_id": "invoice-agent",
    }
    if advisory:
        body["mode"] = "advisory"
    headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
    return _request("POST", "/v1/judge", body, headers)


def act_on(result: dict) -> str:
    """Map next_step.action (pass | retry | escalate) to what the agent does."""
    step = result.get("next_step") or {}
    action = step.get("action")
    receipt = (result.get("receipt") or {}).get("receipt_id")
    print(f"verdict={result.get('verdict')} score={result.get('score')} "
          f"verification={result.get('verification')} engine={result.get('engine')}")
    print(f"next_step={action} error_type={step.get('error_type')} hint={step.get('hint')}")
    dup = result.get("duplicate")
    if dup:  # present only when a duplicate check was sent; carries no invoice data
        print(f"duplicate.status={dup.get('status')} stored={dup.get('stored')} "
              f"matches={[m.get('rule') for m in dup.get('matches') or []]}")
    if result.get("mode") == "advisory":
        print(f"advisory: recommended_action={result.get('recommended_action')} "
              f"decision_owner={result.get('decision_owner')}")
    print(f"receipt_id={receipt}")
    if action == "pass":
        print("-> PROCEED: payment may go out (keep the receipt for your auditor)")
    elif action == "retry":
        print("-> BLOCK: send the hint back to the agent and fix before paying")
    elif step.get("error_type") in ("duplicate_invoice", "possible_duplicate"):
        print("-> HOLD: possible double payment, hand to a human approver")
    else:
        print("-> ESCALATE: stop and hand to a human approver")
    return action or "escalate"


# ---------- audit export ----------

def export_receipts(fmt: str = "jsonl", since: str | None = None, limit: int = 1000) -> str:
    """GET /v1/receipts/export (free, no call used). Returns one page; follow
    next_cursor (json) or the X-Next-Cursor header for more. Only rows within the
    key's retention_days (default 1, max 90) are in the log. Verify scripts:
    https://screwtape.ai/docs/#audit-export"""
    q = f"format={fmt}&limit={limit}" + (f"&from={since}" if since else "")
    return _request("GET", f"/v1/receipts/export?{q}", raw=True)


def delete_fingerprints() -> dict:
    """DELETE /v1/dedupe/fingerprints: remove every fingerprint this key stored."""
    return _request("DELETE", "/v1/dedupe/fingerprints")
