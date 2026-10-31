from recon.takeover import TakeoverChecker


class FakeRunner:
    def __init__(self, lines, active=True):
        self.lines = lines
        self._active = active
        self.calls = []

    def active(self):
        return self._active

    def run(self, cmd, **kwargs):
        self.calls.append(cmd)
        return list(self.lines)


def test_flags_dangling_github_pages(monkeypatch):
    import recon.takeover as takeover

    monkeypatch.setattr(takeover, "tool_path", lambda name: "dnsx")
    runner = FakeRunner(["api.example.com [CNAME foo.github.io.]"])
    checker = TakeoverChecker(runner)
    checker.fetch = lambda url: (404, "<h1>There isn\u2019t a GitHub Pages site here.</h1>")

    results = {"api.example.com": {"url": "https://api.example.com", "status": 200}}
    takeovers = checker.check(["api.example.com"], results)

    assert takeovers["api.example.com"]["verdict"] == "LIKELY"
    assert takeovers["api.example.com"]["service"] == "GitHub Pages"
    assert results["api.example.com"]["takeover"] == "LIKELY"


def test_ignores_live_service(monkeypatch):
    import recon.takeover as takeover

    monkeypatch.setattr(takeover, "tool_path", lambda name: "dnsx")
    runner = FakeRunner(["app.example.com [CNAME bar.herokuapp.com.]"])
    checker = TakeoverChecker(runner)
    checker.fetch = lambda url: (200, "<h1>My real app</h1>")

    results = {"app.example.com": {"url": "https://app.example.com", "status": 200}}
    assert checker.check(["app.example.com"], results) == {}
    assert "takeover" not in results["app.example.com"]


def test_marks_possible_when_service_is_unreachable(monkeypatch):
    import recon.takeover as takeover

    monkeypatch.setattr(takeover, "tool_path", lambda name: "dnsx")
    runner = FakeRunner(["old.example.com [CNAME dead.netlify.app.]"])
    checker = TakeoverChecker(runner)
    checker.fetch = lambda url: (0, "")

    results = {}
    takeovers = checker.check(["old.example.com"], results)
    assert takeovers["old.example.com"]["verdict"] == "POSSIBLE"


def test_uses_httpx_cnames_when_dnsx_missing(monkeypatch):
    import recon.takeover as takeover

    monkeypatch.setattr(takeover, "tool_path", lambda name: None)
    runner = FakeRunner([])
    checker = TakeoverChecker(runner)
    checker.fetch = lambda url: (404, "The specified bucket does not exist")

    results = {"cdn.example.com": {"cname": ["bucket.s3.amazonaws.com."], "status": 200}}
    takeovers = checker.check(["cdn.example.com"], results)
    assert takeovers["cdn.example.com"]["service"] == "AWS S3"
    assert runner.calls == []


def test_parses_modern_dnsx_cname_format(monkeypatch):
    """dnsx 1.3 prints ``host [CNAME] [target]``."""
    import recon.takeover as takeover

    monkeypatch.setattr(takeover, "tool_path", lambda name: "dnsx")
    runner = FakeRunner(["www.example.com [CNAME] [bucket.s3.amazonaws.com] "])
    checker = TakeoverChecker(runner)
    checker.fetch = lambda url: (0, "")

    results = {}
    takeovers = checker.check(["www.example.com"], results)
    assert takeovers["www.example.com"]["service"] == "AWS S3"
    assert takeovers["www.example.com"]["cname"] == "bucket.s3.amazonaws.com"


def test_ignores_malformed_dnsx_lines(monkeypatch):
    import recon.takeover as takeover

    monkeypatch.setattr(takeover, "tool_path", lambda name: "dnsx")
    runner = FakeRunner(["garbage line", ""])
    checker = TakeoverChecker(runner)
    assert checker.check(["www.example.com"], {}) == {}


def test_skips_ip_and_plain_a_records(monkeypatch):
    import recon.takeover as takeover

    monkeypatch.setattr(takeover, "tool_path", lambda name: "dnsx")
    runner = FakeRunner(["www.example.com [93.184.216.34]"])
    checker = TakeoverChecker(runner)
    checker.fetch = lambda url: (200, "ok")
    assert checker.check(["www.example.com"], {}) == {}
