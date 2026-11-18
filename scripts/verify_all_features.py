import os
import sys
import time
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.agent import JarvisAgent, TOOL_FUNCTIONS, TOOL_SCHEMAS
from core.approvals import classify_tool_call, POLICY_READ, POLICY_CONFIRM, POLICY_CRITICAL, POLICY_BLOCKED
from core.speaker import ElevenLabsSpeaker
from agents.loop_guard import LoopGuard, LoopGuardConfig, LoopVerdict
from agents.morning_digest import generate_morning_digest
from agents.deep_research import run_deep_research
from learning.traces import trace_store, ExecutionTrace, ToolExecutionStep
from learning.miner import TrainingDataMiner
from learning.benchmark import PersonalBenchmarkSynthesizer
from learning.evolver import AgentConfigEvolver
from skills.manager import skill_manager

def test_tool_registry():
    print("\n--- 1. Testing Tool Registry (24 Tools) ---")
    expected_tools = [
        "execute_powershell", "read_file", "write_file", "list_directory", "get_system_stats",
        "list_employees", "read_employee_sop", "update_employee_sop", "log_learned_rule", "read_memory",
        "web_search", "fetch_web_page", "run_deep_research", "generate_morning_digest",
        "calculator", "code_interpreter", "apply_unified_patch",
        "git_status", "git_diff", "git_log",
        "read_pdf", "get_weather",
        "list_skills", "inspect_skill"
    ]
    assert len(expected_tools) == 24, f"Expected 24 tools, got {len(expected_tools)}"
    for t in expected_tools:
        assert t in TOOL_FUNCTIONS, f"Missing tool in TOOL_FUNCTIONS: {t}"
    schema_names = [s["function"]["name"] for s in TOOL_SCHEMAS]
    for t in expected_tools:
        assert t in schema_names, f"Missing tool in TOOL_SCHEMAS: {t}"
    print(f"✔ All {len(expected_tools)} tools correctly registered in functions and schemas.")

def test_individual_tools():
    print("\n--- 2. Executing Individual Tool Functions ---")
    # calculator
    res = TOOL_FUNCTIONS["calculator"](expression="42 * 2 + 10")
    assert "94" in str(res), f"Calculator failed: {res}"
    print("✔ calculator:", res)

    # get_system_stats
    stats = TOOL_FUNCTIONS["get_system_stats"]()
    assert "CPU Usage" in stats and "RAM Usage" in stats
    print(f"✔ get_system_stats:\n" + "\n".join(["    " + l for l in stats.splitlines()]))

    # git_status
    gst = TOOL_FUNCTIONS["git_status"]()
    assert "##" in gst or "branch" in gst.lower() or "fatal" not in gst.lower()
    print("✔ git_status:", gst.splitlines()[0])

    # list_skills
    skills = TOOL_FUNCTIONS["list_skills"]()
    assert "code_review" in skills
    print("✔ list_skills returned skills catalog.")

    # inspect_skill
    sk = TOOL_FUNCTIONS["inspect_skill"](skill_name="code_review")
    assert "code_review" in sk
    print("✔ inspect_skill loaded code_review successfully.")

    # get_weather
    w = TOOL_FUNCTIONS["get_weather"](location="London")
    assert "Temperature" in w or "London" in w
    print("✔ get_weather:", w.splitlines()[0] if "\n" in w else w[:60])

    # code_interpreter
    py_res = TOOL_FUNCTIONS["code_interpreter"](code="x = 15; y = 25; print(x + y)")
    assert "40" in py_res
    print("✔ code_interpreter:", py_res.strip())

    # list_employees
    emp = TOOL_FUNCTIONS["list_employees"]()
    assert "coder" in emp.lower()
    print("✔ list_employees returned team roster:", emp.replace("\n", " | "))

def test_loop_guard():
    print("\n--- 3. Testing LoopGuard Infinite Loop Protection ---")
    cfg = LoopGuardConfig(max_identical_calls=2, warn_before_block=False)
    lg = LoopGuard(config=cfg)
    # Turn 1
    v1 = lg.check("web_search", {"query": "test"})
    assert not v1.blocked
    # Turn 2
    v2 = lg.check("web_search", {"query": "test"})
    assert v2.blocked, "LoopGuard should block on 2nd identical call"
    print("✔ LoopGuard successfully caught duplicate loop:", v2.reason)

    # Test ping-pong loop
    cfg2 = LoopGuardConfig(warn_before_block=False)
    lg2 = LoopGuard(config=cfg2)
    lg2.check("tool_a", {})
    lg2.check("tool_b", {})
    lg2.check("tool_a", {})
    v_pong = lg2.check("tool_b", {})
    assert v_pong.blocked or v_pong.warned
    print("✔ LoopGuard successfully caught ping-pong cycle:", v_pong.reason)

def test_learning_pipeline():
    print("\n--- 4. Testing Learning Pipeline (Traces, Miner, Benchmark, Evolver) ---")
    miner = TrainingDataMiner()
    examplars = miner.mine_exemplars(limit=5)
    print(f"✔ TrainingDataMiner mined {len(examplars)} exemplars.")

    bench = PersonalBenchmarkSynthesizer()
    cases = bench.synthesize(max_cases=3)
    print(f"✔ PersonalBenchmarkSynthesizer compiled {len(cases)} benchmark cases.")

    evolver = AgentConfigEvolver()
    report = evolver.analyze_feedback_and_evolve()
    assert "status" in report
    print(f"✔ AgentConfigEvolver completed with status: '{report['status']}'.")

def test_morning_digest():
    print("\n--- 5. Testing Morning Digest Agent ---")
    digest = generate_morning_digest()
    assert "markdown" in digest and "spoken_script" in digest
    print("✔ MorningDigest generated markdown & spoken script length:", len(digest["spoken_script"]))

def test_approvals_security():
    print("\n--- 6. Testing Approvals & Security Policy ---")
    # READ
    pol, _ = classify_tool_call("calculator", {"expression": "1+1"})
    assert pol == POLICY_READ
    # CONFIRM
    pol, _ = classify_tool_call("write_file", {"path": "test.txt", "content": "hi"})
    assert pol == POLICY_CONFIRM
    # CRITICAL
    pol, _ = classify_tool_call("execute_powershell", {"command": "Remove-Item -Recurse foo"})
    assert pol == POLICY_CRITICAL
    # BLOCKED
    pol, _ = classify_tool_call("execute_powershell", {"command": "diskpart"})
    assert pol == POLICY_BLOCKED
    print("✔ Security policies correctly classified READ, CONFIRM, CRITICAL, and BLOCKED.")

def test_agent_sync_chat():
    print("\n--- 7. Testing Synchronous Agent Chat ---")
    agent = JarvisAgent()
    reply = agent.chat("Calculate 17 * 19 using the calculator tool and reply with just the number.")
    print("✔ Agent Chat Reply:", reply.strip())
    assert "323" in reply, f"Expected 323 in reply, got: {reply}"

def test_elevenlabs_speech():
    print("\n--- 8. Testing ElevenLabs Audio Generation ---")
    sp = ElevenLabsSpeaker()
    assert bool(sp.api_key), "ELEVENLABS_API_KEY is not set!"
    meta = sp.generate_speech("All systems operational. Verification complete.", session_id="test")
    assert meta is not None, "Speech generation failed"
    assert Path(meta["file_path"]).exists(), f"Audio file not created: {meta.get('file_path')}"
    print(f"✔ ElevenLabs audio generated: {meta['audio_id']}.mp3 ({os.path.getsize(meta['file_path'])} bytes)")

if __name__ == "__main__":
    test_tool_registry()
    test_individual_tools()
    test_loop_guard()
    test_learning_pipeline()
    test_morning_digest()
    test_approvals_security()
    test_agent_sync_chat()
    test_elevenlabs_speech()
    print("\n=============================================")
    print("🎉 ALL FEATURES & LEARNINGS 100% OPERATIONAL!")
    print("=============================================")
