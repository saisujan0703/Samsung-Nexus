import asyncio
import json
import httpx
import websockets

async def run_query(query: str):
    print("=" * 60)
    print(f"TESTING QUERY: {query}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post("http://127.0.0.1:8000/api/session", json={})
        sid = resp.json()["session_id"]
    print(f"Session created: {sid}")

    uri = f"ws://127.0.0.1:8000/ws/{sid}"
    async with websockets.connect(uri, ping_interval=20, ping_timeout=120) as ws:
        # Send query via WebSocket frame (exact frontend mechanism)
        await ws.send(json.dumps({"type": "user_input", "text": query}))
        print("Input sent via WebSocket. Awaiting events...")

        routing_decision = None
        full_chunks = []
        final_text = ""

        while True:
            raw_msg = await ws.recv()
            evt = json.loads(raw_msg)
            etype = (evt.get("event_type") or evt.get("type", "")).upper()
            payload = evt.get("data") or evt.get("payload") or {}

            if etype == "ROUTING_DECISION":
                routing_decision = payload
                print(f"[EVENT] ROUTING_DECISION: {routing_decision}")
            elif etype == "TEXT_CHUNK":
                chunk = payload.get("text", "")
                full_chunks.append(chunk)
            elif etype == "RESPONSE_COMPLETED":
                final_text = payload.get("text", "")
                print(f"[EVENT] RESPONSE_COMPLETED (final text length: {len(final_text)})")
                break
            elif etype == "ERROR":
                print(f"[EVENT] ERROR: {payload}")
                break

        full_streamed = "".join(full_chunks).strip()
        result_text = final_text or full_streamed

        print("\n--- ACTUAL FULL RESPONSE ---")
        print(result_text)
        print("--- END ACTUAL RESPONSE ---\n")
        print(f"Character count: {len(result_text)}")
        return result_text

async def main():
    # Test 1: IPL 2025 Complete Schedule
    resp1 = await run_query("Give me the complete schedule of IPL 2025")
    
    # Test 2: Completely different historical schedule request (UEFA Euro 2024 knockout stage)
    resp2 = await run_query("Give me the complete schedule of the UEFA Euro 2024 knockout stage")

if __name__ == "__main__":
    asyncio.run(main())
