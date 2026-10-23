"""Drop-in Screwtape steps for CrewAI.

1. screwtape_guardrail: pass as Task(guardrail=...). CrewAI calls it with the task
   output; returning (False, hint) makes the agent retry with Screwtape's hint.
2. ScrewtapeInvoiceCheckTool: a tool the agent can call itself before deciding.

Both call POST /v1/judge with required_fields + sum (+ optional duplicate) checks.
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.screwtape_gate import judge_invoice_decision


def _parse(raw: str) -> dict:
    return json.loads(str(raw).strip().strip("`").removeprefix("json").strip())


def make_guardrail(invoice_text: str, duplicate: bool = True, advisory: bool = False):
    """Returns a CrewAI task guardrail: (output) -> (ok, value_or_feedback)."""
    def screwtape_guardrail(output):
        raw = getattr(output, "raw", output)
        try:
            decision = _parse(raw)
        except ValueError:
            return False, "Return only a JSON object."
        result = judge_invoice_decision(decision, invoice_text,
                                        duplicate=duplicate, advisory=advisory)
        step = result.get("next_step") or {}
        if step.get("action") == "pass":
            return True, json.dumps({"decision": decision,
                                     "receipt_id": (result.get("receipt") or {}).get("receipt_id")})
        if step.get("action") == "retry":
            return False, step.get("hint", "Fix the invoice fields and try again.")
        # escalate (incl. duplicate_invoice / possible_duplicate): do not let the agent retry
        raise RuntimeError(f"Escalate to a human approver: {step.get('error_type')}")
    return screwtape_guardrail


try:
    from crewai.tools import BaseTool

    class ScrewtapeInvoiceCheckTool(BaseTool):
        name: str = "screwtape_invoice_check"
        description: str = ("Check an invoice decision JSON before paying. Input: the JSON "
                            "string. Returns next_step.action (pass, retry, escalate) and a hint.")
        invoice_text: str = ""

        def _run(self, decision_json: str) -> str:
            r = judge_invoice_decision(_parse(decision_json), self.invoice_text, duplicate=True)
            return json.dumps({"verdict": r.get("verdict"), "next_step": r.get("next_step"),
                               "duplicate": r.get("duplicate"),
                               "receipt_id": (r.get("receipt") or {}).get("receipt_id")})
except ImportError:  # crewai not installed: the guardrail still works on its own
    pass
