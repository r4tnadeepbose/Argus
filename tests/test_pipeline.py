from recon.pipeline import PipelineConfig, ReconPipeline
from recon.state import RunStore


class FakeRunner:
    def __init__(self, active=True):
        self._active = active

    def active(self):
        return self._active

    def run(self, *_args, **_kwargs):
        return []

    def kill(self):
        pass


class MockPipeline(ReconPipeline):
    """Deterministic stand-in for subfinder/httpx/dnsx."""

    def __init__(self, *args, stop_after_first_dnsx=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_after_first_dnsx = stop_after_first_dnsx

    def _subfinder(self, domain, use_all):
        return {f"www.{domain}", f"api.{domain}"}

    def _httpx(self, hosts, codes, use_shots):
        return {
            host: {
                "url": f"https://{host}",
                "status": 200,
                "title": f"title {host}",
                "tech": ["nginx"],
                "cname": [],
                "screenshot": "",
                "takeover": "",
            }
            for host in hosts
        }

    def _dnsx(self, fqdns):
        if self.stop_after_first_dnsx:
            self.stop_after_first_dnsx = False
            self.runner._active = False
            return set()
        return {fqdn for fqdn in fqdns if fqdn.startswith("dev.")}


def build(tmp_path, run_id="test1", **overrides):
    store = RunStore(runs_dir=tmp_path / "runs", resume_file=tmp_path / "resume.cfg")
    config = dict(domain="example.com", cycles=2, codes=[200], use_shots=False,
                  use_takeover=False, wordlist=["dev", "prod"])
    config.update(overrides)
    cfg = PipelineConfig(**config)
    runner = FakeRunner()
    pipeline = MockPipeline(cfg, runner, store, log=lambda _msg: None, run_id=run_id)
    return pipeline, store


def test_full_recursive_run(tmp_path):
    pipeline, store = build(tmp_path)
    assert pipeline.run() is True
    assert pipeline.completed
    # 3 hosts from cycle 1, then the 3 resolved hosts plus 6 subdomains in cycle 2.
    assert len(pipeline.results) == 12
    assert "dev.api.example.com" in pipeline.results  # resolved hosts get probed
    assert store.state_path("test1").is_file()
    assert store.results_path("test1").is_file()
    assert store.read_resume_cfg()["status"] == "running"


def test_stop_and_resume_restores_every_host(tmp_path):
    pipeline, store = build(tmp_path, run_id="test2")
    pipeline.stop_after_first_dnsx = True
    assert pipeline.run() is False
    assert pipeline.completed is False

    state = store.load_state("test2")
    assert state is not None
    assert state["phase"] == "brute"
    assert store.read_resume_cfg()["status"] == "running"

    resumed_cfg = PipelineConfig(
        domain=state["domain"], cycles=state["cycles"], codes=state["codes"],
        use_shots=False, use_takeover=False, wordlist=state["wordlist"])
    resumed = MockPipeline(resumed_cfg, FakeRunner(active=True), store,
                           log=lambda _msg: None, run_id="test2")
    assert resumed.run(state) is True
    assert resumed.completed
    assert len(resumed.results) == 12


def test_single_cycle_does_not_brute(tmp_path):
    pipeline, _store = build(tmp_path, cycles=1)
    assert pipeline.run() is True
    assert len(pipeline.results) == 3


def test_brute_disabled_stops_after_first_probe(tmp_path):
    pipeline, _store = build(tmp_path, use_brute=False)
    assert pipeline.run() is True
    assert len(pipeline.results) == 3
    assert "dev.example.com" not in pipeline.results


def test_default_wordlist_used_when_empty():
    cfg = PipelineConfig(domain="example.com")
    assert cfg.wordlist
    assert "www" in cfg.wordlist
