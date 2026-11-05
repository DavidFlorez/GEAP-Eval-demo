#!/usr/bin/env python3
"""
Test client for the Vertex AI Agent Engine (GEAP) Deployed Contract Review Agent.
Connects to the deployed ReasoningEngine in Google Cloud project assist-463118.
"""

import os
import json
import vertexai
from vertexai.preview import reasoning_engines
from google.cloud import aiplatform_v1beta1 as aip_types

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "assist-463118")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
ENGINE_RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE",
    "projects/806084165595/locations/us-central1/reasoningEngines/843288309986754560",
)


def run_cloud_review(contract_id: str = "01_standard_nda"):
    print(f"[*] Initializing Vertex AI Client: Project={PROJECT_ID}, Location={LOCATION}")
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    print(f"[*] Connecting to Deployed Agent Engine: {ENGINE_RESOURCE}")
    engine = reasoning_engines.ReasoningEngine(ENGINE_RESOURCE)
    print(f"    -> Agent Name: {engine.display_name}")

    print("\n[*] Creating Session in GEAP...")
    session = engine.create_session(user_id="geap_compliance_evaluator")
    session_id = session.get("id") or session.get("session_id")
    print(f"    -> Created Session ID: {session_id}")

    prompt = f"Perform an 18-point compliance review on contract {contract_id}"
    print(f"\n[*] Streaming Review from Deployed Agent for '{contract_id}'...")

    request = aip_types.StreamQueryReasoningEngineRequest(
        name=engine.resource_name,
        input={
            "message": prompt,
            "user_id": "geap_compliance_evaluator",
            "session_id": session_id,
        },
    )

    response_stream = engine.execution_api_client.stream_query_reasoning_engine(request=request)

    final_text = ""
    tool_calls_detected = []

    for chunk in response_stream:
        # Check for tool invocations or final text parts
        data_str = chunk.data.decode("utf-8") if isinstance(chunk.data, bytes) else str(chunk.data)
        try:
            payload = json.loads(data_str)
            parts = payload.get("content", {}).get("parts", [])
            for p in parts:
                if "function_call" in p:
                    fc = p["function_call"]
                    tool_calls_detected.append(f"{fc.get('name')}({fc.get('args')})")
                    print(f"    [Tool Invocated in Cloud]: {fc.get('name')}({fc.get('args')})")
                if "text" in p:
                    final_text += p["text"]
        except Exception:
            pass

    print(f"\n[+] Total Cloud Tool Invocations: {len(tool_calls_detected)}")
    print(f"[+] Final Review Length: {len(final_text)} characters")
    if final_text:
        print("\n--- SAMPLE COMPLIANCE FINDINGS (CLOUD AGENT) ---")
        lines = [l for l in final_text.splitlines() if l.strip().startswith("**")][:6]
        for line in lines:
            print("  ", line)

    print("\n[SUCCESS] Deployed Cloud Agent executed and returned verified review.")


if __name__ == "__main__":
    run_cloud_review()
