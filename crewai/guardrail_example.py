"""CrewAI Task with a Screwtape guardrail (needs crewai and your LLM key).

python guardrail_example.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from crewai import Agent, Task, Crew
from common.sample_invoices import INVOICE_TEXT_DUP
from screwtape_steps import make_guardrail

clerk = Agent(role="AP clerk", goal="Extract invoice fields and decide whether to pay",
              backstory="You process vendor invoices.", allow_delegation=False)
task = Task(
    description=("Read this invoice and return ONLY JSON with keys invoice_id, vendor, "
                 "invoice_date (YYYY-MM-DD), currency, items (list of {desc, amount}), "
                 "subtotal, tax, total, decision ('approve_and_pay' or 'reject'):\n"
                 + INVOICE_TEXT_DUP),
    expected_output="A JSON object", agent=clerk,
    guardrail=make_guardrail(INVOICE_TEXT_DUP, duplicate=True))

if __name__ == "__main__":
    print(Crew(agents=[clerk], tasks=[task]).kickoff())
