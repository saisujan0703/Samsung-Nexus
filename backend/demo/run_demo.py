"""
SURU AI Demo Runner — Command-line live demonstration of interruptible agent flow.

Simulates live voice/text interactions:
1. Goal: "Plan a 3-day Chennai trip for 15000 rupees."
2. Execution starts
3. Interruption: "Wait. I am travelling with my parents. Avoid places requiring lots of walking."
4. Plan Diff computed (KEEP, CANCEL, MODIFY, ADD)
5. Replanning applied, execution resumes
6. Budget update to 20000
7. Complete goal change to "Help me prepare for an interview"
"""

import asyncio
import sys
from backend.agent.orchestrator import AgentState
from backend.memory.session_memory import session_memory
from backend.realtime.events import EventType, NexusEvent


def print_banner():
    print("=" * 70)
    print("  SURU AI — Interruptible Real-Time Agent")
    print("  'Hey SURU — An AI agent that doesn't restart when you change your mind.'")
    print("=" * 70)


async def run_live_demo():
    print_banner()

    session_id = "demo_session"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    async def log_event(event: NexusEvent):
        if event.type == EventType.AGENT_STATE_CHANGED:
            print(f"  [STATE] >>> {event.data.get('state')} (reason: {event.data.get('reason')})")
        elif event.type == EventType.INTERRUPTION_DETECTED:
            print(f"  [INTERRUPTION] Detected: '{event.data.get('text')}'")
        elif event.type == EventType.INTERRUPTION_CLASSIFIED:
            print(f"  [CLASSIFIED] Type: {event.data.get('type')} | Confidence: {event.data.get('confidence')} | Reason: {event.data.get('reasoning')}")
        elif event.type == EventType.PLAN_DIFF_COMPUTED:
            diff = event.data.get("diff", {})
            print(f"  [PLAN DIFF] {diff.get('summary')}")
            if diff.get("modify"):
                for m in diff["modify"]:
                    print(f"     -> MODIFY: {m.get('task_id')} ({m.get('reason')})")
        elif event.type == EventType.TASK_STARTED:
            print(f"  [TASK] Started: {event.data.get('task_id')} ({event.data.get('tool')})")
        elif event.type == EventType.TASK_COMPLETED:
            print(f"  [TASK] Completed: {event.data.get('task_id')} -> {event.data.get('output_summary', '')[:60]}")
        elif event.type == EventType.TASK_CANCELLED:
            print(f"  [TASK] Cancelled: {event.data.get('task_id')} ({event.data.get('reason')})")

    event_bus.subscribe_all(log_event)

    print("\n--- STEP 1: INITIAL GOAL ---")
    prompt = "Plan a 3-day Chennai trip for 15000 rupees."
    print(f"User: \"{prompt}\"")
    await orchestrator.handle_user_input(prompt)

    # Let execution run for 0.4 seconds
    await asyncio.sleep(0.4)

    print("\n--- STEP 2: USER INTERRUPTS (Constraint Change) ---")
    interruption = "Wait. I am travelling with my parents. Avoid places requiring lots of walking."
    print(f"User: \"{interruption}\"")
    await orchestrator.handle_user_input(interruption)

    # Let execution run for 0.4 seconds with new plan
    await asyncio.sleep(0.4)

    print("\n--- STEP 3: SECOND INTERRUPTION (Budget Increase) ---")
    budget_mod = "Actually increase the budget to 20000."
    print(f"User: \"{budget_mod}\"")
    await orchestrator.handle_user_input(budget_mod)

    await asyncio.sleep(0.3)

    print("\n--- STEP 4: THIRD INTERRUPTION (Complete Goal Pivot) ---")
    pivot = "Forget the trip. Help me prepare for an interview instead."
    print(f"User: \"{pivot}\"")
    await orchestrator.handle_user_input(pivot)

    await asyncio.sleep(0.3)

    # Clean shutdown
    await orchestrator.executor.stop()
    await session_memory.delete(session_id)
    print("\n" + "=" * 70)
    print("  DEMO COMPLETED SUCCESSFULLY: ALL INTERRUPTIONS HANDLED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_live_demo())
