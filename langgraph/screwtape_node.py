"""Reusable Screwtape judge node + router for any LangGraph graph.

    from screwtape_node import make_judge_node, route
    g.add_node("judge", make_judge_node(invoice_text, duplicate=True))
    g.add_conditional_edges("judge", route, {"pass": "pay", "retry": "fix", "escalate": "human"})

State needs a "decision" dict. The node writes "result" and "action".
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.screwtape_gate import judge_invoice_decision, act_on


def make_judge_node(invoice_text: str, duplicate: bool = False, advisory: bool = False):
    def judge(state: dict) -> dict:
        result = judge_invoice_decision(state["decision"], invoice_text,
                                        duplicate=duplicate, advisory=advisory)
        return {"result": result, "action": act_on(result)}
    return judge


def route(state: dict) -> str:
    """pass -> pay, retry -> fix (send hint back), escalate -> human (incl. duplicates)."""
    return state.get("action") or "escalate"
