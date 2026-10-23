"""CrewAI agent proposes an invoice decision; Screwtape /v1/judge gates it.

python main.py --mock         # no LLM key needed: uses a canned agent decision
python main.py --mock --bad   # canned decision with a wrong total
python main.py                # real CrewAI agent (needs an LLM key, e.g. OPENAI_API_KEY)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json, sys
from common.sample_invoices import INVOICE_TEXT, GOOD, BAD
from common.screwtape_gate import judge_invoice_decision, act_on


def crew_decision() -> dict:
    from crewai import Agent, Task, Crew
    clerk = Agent(role="AP clerk", goal="Extract invoice fields and decide whether to pay",
                  backstory="You process vendor invoices.", allow_delegation=False)
    task = Task(
        description=("Read this invoice and return ONLY JSON with keys invoice_id, vendor, "
                     "items (list of {desc, amount}), subtotal, tax, total, decision "
                     "('approve_and_pay' or 'reject'):\n" + INVOICE_TEXT),
        expected_output="A JSON object", agent=clerk)
    out = str(Crew(agents=[clerk], tasks=[task]).kickoff()).strip().strip("`")
    return json.loads(out.removeprefix("json").strip())


if __name__ == "__main__":
    mock = "--mock" in sys.argv
    decision = (BAD if "--bad" in sys.argv else GOOD) if mock else crew_decision()
    print("agent decision:", json.dumps(decision))
    action = act_on(judge_invoice_decision(decision, INVOICE_TEXT))
    sys.exit(0 if action == "pass" else 1)
