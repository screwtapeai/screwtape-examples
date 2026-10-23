"""AutoGen (autogen-agentchat 0.4+): Screwtape as a tool the AP agent must call
before it approves a payment.

python main.py --stub          # no LLM: calls the tool directly with a canned decision
python main.py --stub --bad    # canned decision with a wrong total
python main.py                 # real AssistantAgent (needs OPENAI_API_KEY)

Note: Microsoft now points new projects to Microsoft Agent Framework; the tool
function below is plain Python and works there too.
"""
import asyncio, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common.sample_invoices import INVOICE_TEXT_DUP, GOOD_DUP
from common.screwtape_gate import judge_invoice_decision, act_on


async def screwtape_invoice_check(decision_json: str) -> str:
    """Check an invoice decision JSON before paying. Returns next_step.action
    (pass, retry, escalate), a hint, the duplicate status and a receipt id."""
    result = judge_invoice_decision(json.loads(decision_json), INVOICE_TEXT_DUP,
                                    duplicate=True, advisory="--advisory" in sys.argv)
    act_on(result)
    return json.dumps({"next_step": result.get("next_step"),
                       "duplicate": result.get("duplicate"),
                       "recommended_action": result.get("recommended_action"),
                       "receipt_id": (result.get("receipt") or {}).get("receipt_id")})


async def run_agent():
    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    agent = AssistantAgent(
        "ap_clerk", model_client=OpenAIChatCompletionClient(model="gpt-4o-mini"),
        tools=[screwtape_invoice_check],
        system_message=("Extract the invoice to JSON (invoice_id, vendor, invoice_date, currency, "
                        "items[{desc, amount}], subtotal, tax, total, decision). Always call "
                        "screwtape_invoice_check before approving. Approve only if "
                        "next_step.action is pass; on retry fix and re-check; on escalate stop."))
    result = await agent.run(task=INVOICE_TEXT_DUP)
    print(result.messages[-1].content)


if __name__ == "__main__":
    if "--stub" in sys.argv:  # STUB agent: canned decision; swap in your own model
        decision = dict(GOOD_DUP, total=659.00) if "--bad" in sys.argv else GOOD_DUP
        out = json.loads(asyncio.run(screwtape_invoice_check(json.dumps(decision))))
        sys.exit(0 if out["next_step"]["action"] == "pass" else 1)
    asyncio.run(run_agent())
