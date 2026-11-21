from agents.loop_guard import LoopGuard


def test_distinct_document_steps_are_not_a_repeated_cycle():
    guard = LoopGuard()
    steps = [
        ('keyboard_hotkey', {'target_window': 'Notepad', 'keys': ['ctrl', 'n']}),
        ('keyboard_type', {'target_window': 'Notepad', 'text': 'Action plan'}),
        ('keyboard_hotkey', {'target_window': 'Notepad', 'keys': ['ctrl', 'shift', 's']}),
        ('keyboard_type', {'target_window': 'Save As', 'text': 'action-plan.txt'}),
        ('keyboard_hotkey', {'target_window': 'Save As', 'keys': ['enter']}),
        ('keyboard_type', {'target_window': 'Notepad', 'text': 'Next document'}),
    ]
    for name, args in steps:
        verdict = guard.check(name, args)
        assert not verdict.blocked and not verdict.warned, verdict.reason


def test_identical_retry_cycle_still_stops():
    guard = LoopGuard()
    outcomes = [guard.check(name, args) for name, args in [
        ('focus_window', {'title': 'Notepad'}),
        ('keyboard_hotkey', {'target_window': 'Notepad', 'keys': ['ctrl', 's']}),
    ] * 4]
    assert any(v.warned for v in outcomes)
    assert any(v.blocked for v in outcomes)
