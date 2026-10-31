import sys

from recon.runner import CommandRunner


def test_returns_stdout_lines():
    logs = []
    runner = CommandRunner(logs.append, lambda: True)
    out = runner.run([sys.executable, "-c", "print('a');print('b')"])
    assert out == ["a", "b"]
    assert logs[0].startswith("$ ")


def test_line_handler_receives_each_line():
    seen = []
    runner = CommandRunner(lambda _msg: None, lambda: True)
    out = runner.run([sys.executable, "-c", "print('{\"x\": 1}')"],
                     line_handler=seen.append, stream=False)
    assert out and seen == out


def test_line_handler_errors_do_not_abort_run():
    def explode(_line):
        raise ValueError("boom")

    runner = CommandRunner(lambda _msg: None, lambda: True)
    out = runner.run([sys.executable, "-c", "print('x')"], line_handler=explode)
    assert out == ["x"]


def test_stderr_is_drained_and_logged():
    logs = []
    runner = CommandRunner(logs.append, lambda: True)
    out = runner.run([sys.executable, "-c",
                      "import sys; sys.stderr.write('boom\\n')"], stream=False)
    assert out == []
    assert any("[stderr]" in msg and "boom" in msg for msg in logs)


def test_live_stderr_uses_configured_prefix():
    logs = []
    runner = CommandRunner(logs.append, lambda: True)
    runner.run([sys.executable, "-c", "import sys; sys.stderr.write('stat\\n')"],
               live_stderr=True, stats_prefix="[httpx]")
    assert any("[httpx] stat" in msg for msg in logs)


def test_inactive_runner_skips_command():
    logs = []
    runner = CommandRunner(logs.append, lambda: False)
    assert runner.run([sys.executable, "-c", "print('x')"]) == []
    assert logs == []
