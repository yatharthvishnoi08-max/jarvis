import os
import pytest
from tools.web_tools import web_search, fetch_web_page, check_ssrf
from tools.code_tools import calculator, code_interpreter
from tools.dev_tools import git_status, git_log
from tools.doc_tools import get_weather
from agents.loop_guard import LoopGuard, LoopGuardConfig
from learning.traces import TraceStore, ExecutionTrace, ToolExecutionStep
from learning.miner import TrainingDataMiner
from learning.benchmark import PersonalBenchmarkSynthesizer
from skills.manager import SkillManager
from agents.morning_digest import generate_morning_digest

def test_calculator():
    assert calculator("2 + 2") == "4"
    assert calculator("sqrt(16) * 3") == "12.0"
    assert "Error" in calculator("__import__('os')")

def test_code_interpreter():
    # Safe code
    res = code_interpreter("print(sum([1, 2, 3, 4]))")
    assert "10" in res

    # Blocked code
    res_blocked = code_interpreter("import sys\nprint(sys.version)")
    assert "Security Restriction" in res_blocked

def test_ssrf_checker():
    assert check_ssrf("http://127.0.0.1/admin") is not None
    assert check_ssrf("http://169.254.169.254/latest/meta-data") is not None
    assert check_ssrf("https://example.com") is None

def test_git_tools():
    status = git_status()
    assert isinstance(status, str)
    log = git_log(limit=2)
    assert isinstance(log, str) and len(log) > 0

def test_loop_guard():
    guard = LoopGuard(LoopGuardConfig(max_identical_calls=2, warn_before_block=False))
    # First call: OK
    v1 = guard.check("calculator", {"expression": "2+2"})
    assert not v1.blocked
    # Second call: Blocked
    v2 = guard.check("calculator", {"expression": "2+2"})
    assert v2.blocked
    assert "LOOP GUARD TRIPPED" in v2.reason

def test_learning_traces_and_miner(tmp_path):
    store = TraceStore(storage_dir=tmp_path)
    trace = ExecutionTrace(
        trace_id="tr_unit_1",
        session_id="sess_1",
        user_query="What is 10 plus 15?",
        response_text="The answer is 25.",
        timestamp=100.0,
        duration_seconds=0.5,
        model_name="test-model",
        steps=[ToolExecutionStep("calculator", {"expression": "10+15"}, "25", 0.05)],
        feedback_score=1.0
    )
    store.record_trace(trace)
    assert len(store.list_traces()) == 1

    miner = TrainingDataMiner(store=store)
    exemplars = miner.mine_exemplars()
    assert len(exemplars) == 1
    assert exemplars[0]["query"] == "What is 10 plus 15?"

    synth = PersonalBenchmarkSynthesizer(store=store)
    cases = synth.synthesize()
    assert len(cases) == 1
    assert cases[0].category == "computation"

def test_skills_manager(tmp_path):
    mgr = SkillManager(root_dir=tmp_path)
    mgr.install_skill(
        name="test_skill",
        description="A test skill",
        instructions="Step 1: Do testing."
    )
    assert len(mgr.list_skills()) == 1
    skill = mgr.get_skill("test_skill")
    assert skill is not None
    assert "Do testing" in skill.content

def test_morning_digest():
    digest = generate_morning_digest()
    assert "markdown" in digest
    assert "spoken_text" in digest
    assert "Host System Status" in digest["markdown"]
