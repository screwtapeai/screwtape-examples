"""LangGraph: agent node -> judge node -> conditional edge on next_step.action.

python main.py          # canned agent decision (no LLM key needed)
python main.py --bad    # canned decision with a wrong total
python main.py --three --bad  # 3-line-item invoice with a wrong total
Swap propose() for an LLM call to use a real model.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import sys
from typing import TypedDict
from langgraph.graph import StateGraph, END
from common.sample_invoices import INVOICE_TEXT, GOOD, BAD, INVOICE_TEXT_3, GOOD_3, BAD_3
from common.screwtape_gate import judge_invoice_decision, act_on


class State(TypedDict, total=False):
    decision: dict
    result: dict
    action: str


THREE = "--three" in sys.argv
TEXT = INVOICE_TEXT_3 if THREE else INVOICE_TEXT


def propose(state: State) -> State:  # STUB agent: canned decision; replace with your LLM
    if THREE:
        return {"decision": BAD_3 if "--bad" in sys.argv else GOOD_3}
    return {"decision": BAD if "--bad" in sys.argv else GOOD}


def judge(state: State) -> State:
    result = judge_invoice_decision(state["decision"], TEXT)
    return {"result": result, "action": act_on(result)}


def pay(state: State) -> State:
    print("PAID", state["decision"]["invoice_id"], "receipt",
          (state["result"].get("receipt") or {}).get("receipt_id"))
    return {}


def fix(state: State) -> State:
    print("BLOCKED, agent should fix:", state["result"]["next_step"]["hint"])
    return {}


def human(state: State) -> State:
    print("ESCALATED to a human approver")
    return {}


g = StateGraph(State)
for name, fn in [("propose", propose), ("judge", judge), ("pay", pay), ("fix", fix), ("human", human)]:
    g.add_node(name, fn)
g.set_entry_point("propose")
g.add_edge("propose", "judge")
g.add_conditional_edges("judge", lambda s: s["action"],
                        {"pass": "pay", "retry": "fix", "escalate": "human"})
for n in ("pay", "fix", "human"):
    g.add_edge(n, END)
app = g.compile()

if __name__ == "__main__":
    out = app.invoke({})
    sys.exit(0 if out.get("action") == "pass" else 1)
