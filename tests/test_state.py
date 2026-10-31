from recon.state import RunStore


def make_store(tmp_path):
    return RunStore(runs_dir=tmp_path / "runs", resume_file=tmp_path / "resume.cfg")


def test_save_and_load_state(tmp_path):
    store = make_store(tmp_path)
    state = {
        "run_id": "20260101_000000",
        "domain": "example.com",
        "cycle": 2,
        "phase": "brute",
        "live_parents": ["api.example.com", "www.example.com"],
        "parent_cursor": 1,
        "index": 42,
        "results": {"api.example.com": {"status": 200}},
    }
    store.save_state(state)

    assert store.state_path("20260101_000000").is_file()
    assert store.load_state("20260101_000000")["cycle"] == 2

    cfg = store.read_resume_cfg()
    assert cfg["run_id"] == "20260101_000000"
    assert cfg["status"] == "running"
    assert cfg["resume_from"] == "www.example.com"
    assert cfg["index"] == "42"


def test_resumable_roundtrip(tmp_path):
    store = make_store(tmp_path)
    store.save_state({"run_id": "r1", "domain": "example.com", "cycle": 1,
                      "phase": "passive", "live_parents": [],
                      "parent_cursor": 0, "index": 0})
    found = store.resumable()
    assert found is not None
    cfg, state = found
    assert cfg["run_id"] == "r1"
    assert state["domain"] == "example.com"


def test_finished_runs_are_not_resumable(tmp_path):
    store = make_store(tmp_path)
    store.save_state({"run_id": "r2", "domain": "example.com", "cycle": 1,
                      "phase": "passive", "live_parents": [],
                      "parent_cursor": 0, "index": 0})
    store.mark_finished("r2", "example.com")
    assert store.resumable() is None


def test_legacy_cfg_without_run_id_is_not_resumable(tmp_path):
    resume = tmp_path / "resume.cfg"
    resume.write_text("resume_from=old.example.com\nindex=1575\n", encoding="utf-8")
    store = make_store(tmp_path)
    assert store.resumable() is None
    assert store.read_resume_cfg()["resume_from"] == "old.example.com"


def test_missing_state_returns_none(tmp_path):
    store = make_store(tmp_path)
    assert store.load_state("nope") is None


def test_write_results_and_history(tmp_path):
    store = make_store(tmp_path)
    store.write_results("r3", "example.com",
                        {"a.example.com": {"status": 200}},
                        {"b.example.com": {"verdict": "LIKELY"}})
    assert store.results_path("r3").is_file()
    assert store.run_ids() == ["r3"]
