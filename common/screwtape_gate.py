"""Tiny client for POST https://screwtape.ai/v1/judge (public API). Shared by crewai/ and langgraph/."""
import json, os, urllib.request, urllib.error

API = os.environ.get("SCREWTAPE_API_URL", "https://screwtape.ai")

def invoice_checks(decision: dict) -> list:
    """required_fields + sum built from however many line items the invoice has."""
    n = len(decision.get("items") or [])
    return [
        {"type": "required_fields",
         "paths": ["invoice_id", "vendor", "subtotal", "tax", "total", "decision"]},
        # items.0.amount + ... + items.N-1.amount + tax must equal total
        {"type": "sum", "parts": [f"items.{i}.amount" for i in range(n)] + ["tax"],
         "total": "total", "tolerance": 0.01},
    ]


def judge_invoice_decision(decision: dict, invoice_text: str) -> dict:
    key = os.environ.get("SCREWTAPE_API_KEY")
    if not key:
        raise SystemExit("Set SCREWTAPE_API_KEY (free key: https://screwtape.ai/signup/)")
    body = {
        "task": "Decide whether to approve and pay this invoice. Return JSON.",
        "agent_output": json.dumps(decision),
        "evidence": [invoice_text],
        "checks": invoice_checks(decision),
        "agent_id": "invoice-agent",
    }
    req = urllib.request.Request(
        f"{API}/v1/judge", data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "screwtape-examples/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode()[:500]}")


def act_on(result: dict) -> str:
    """Map next_step.action (pass | retry | escalate) to what the agent does."""
    step = result.get("next_step") or {}
    action = step.get("action")
    receipt = (result.get("receipt") or {}).get("receipt_id")
    print(f"verdict={result.get('verdict')} score={result.get('score')} "
          f"verification={result.get('verification')} engine={result.get('engine')}")
    print(f"next_step={action} error_type={step.get('error_type')} hint={step.get('hint')}")
    print(f"receipt_id={receipt}")
    if action == "pass":
        print("-> PROCEED: payment may go out (keep the receipt for your auditor)")
    elif action == "retry":
        print("-> BLOCK: send the hint back to the agent and fix before paying")
    else:
        print("-> ESCALATE: stop and hand to a human approver")
    return action or "escalate"
