"""Subprocess execution with streaming logs and cooperative cancellation."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable


class CommandRunner:
    """Run external tools, streaming stdout through a log callback.

    ``should_run`` is a zero-argument callable; when it returns ``False`` the
    runner refuses to start new commands. :meth:`kill` terminates the command
    that is currently running.

    stdout is read on the calling thread. stderr is drained on a helper thread
    so a chatty tool cannot fill the pipe and deadlock the run.
    """

    def __init__(self, log: Callable[[str], None], should_run: Callable[[], bool]):
        self._log = log
        self._should_run = should_run
        self.proc: subprocess.Popen | None = None

    def active(self) -> bool:
        return bool(self._should_run())

    def run(
        self,
        cmd: list[str],
        input_data: str | None = None,
        label: str | None = None,
        stream: bool = True,
        cwd: str | None = None,
        line_handler: Callable[[str], None] | None = None,
        live_stderr: bool = False,
        heartbeat: int | None = None,
        stats_prefix: str = "[stats]",
    ) -> list[str]:
        """Execute *cmd* and return its non-empty stdout lines.

        ``line_handler`` receives each raw stdout line (useful for parsing JSON
        while still keeping stdout available to callers). ``live_stderr`` logs
        stderr lines as they arrive (httpx ``-stats``). ``heartbeat`` logs a
        "still running" line every N seconds.
        """
        if not self.active():
            return []
        name = label or " ".join(cmd)
        self._log(f"$ {name}")
        lines: list[str] = []
        err_lines: list[str] = []
        stop_heartbeat = threading.Event()
        stderr_thread: threading.Thread | None = None
        heartbeat_thread: threading.Thread | None = None
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )

            def drain_stderr() -> None:
                try:
                    for raw in self.proc.stderr:
                        raw = raw.rstrip()
                        if not raw:
                            continue
                        err_lines.append(raw)
                        if live_stderr:
                            self._log(f"  {stats_prefix} {raw[:300]}")
                except (ValueError, OSError):
                    pass

            stderr_thread = threading.Thread(target=drain_stderr, daemon=True)
            stderr_thread.start()

            if heartbeat:
                def beat() -> None:
                    started = time.monotonic()
                    while not stop_heartbeat.wait(heartbeat):
                        if not self.active():
                            break
                        elapsed = int(time.monotonic() - started)
                        self._log(f"  [i] {name} still running ({elapsed}s)")

                heartbeat_thread = threading.Thread(target=beat, daemon=True)
                heartbeat_thread.start()

            if input_data is not None:
                try:
                    self.proc.stdin.write(input_data)
                    self.proc.stdin.close()
                except (BrokenPipeError, OSError):
                    pass

            for line in self.proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                lines.append(line)
                if line_handler:
                    try:
                        line_handler(line)
                    except Exception:  # noqa: BLE001 - a parser bug must not kill the run
                        pass
                if stream:
                    self._log(f"  {line}")
            self.proc.wait()
        except Exception as exc:  # noqa: BLE001 - surface any launch failure in the log
            if self.active():
                self._log(f"  [error] {exc}")
        finally:
            stop_heartbeat.set()
            if stderr_thread:
                stderr_thread.join(timeout=2)
            if err_lines and not live_stderr:
                joined = "\n".join(err_lines).strip()
                if joined:
                    self._log(f"  [stderr] {joined[:500]}")
            self.proc = None
        return lines

    def kill(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.kill()
            except OSError:
                pass
