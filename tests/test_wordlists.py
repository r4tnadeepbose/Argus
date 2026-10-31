from recon.wordlists import DEFAULT_WORDLIST, load_wordlist


def test_empty_path_returns_builtin():
    words, source = load_wordlist("")
    assert words == list(DEFAULT_WORDLIST)
    assert "built-in" in source


def test_missing_file_falls_back(tmp_path):
    words, source = load_wordlist(str(tmp_path / "nope.txt"))
    assert words == list(DEFAULT_WORDLIST)
    assert "built-in" in source


def test_reads_file_and_skips_comments(tmp_path):
    path = tmp_path / "words.txt"
    path.write_text("# comment\napi\n\n  dev  \nprod\n", encoding="utf-8")
    words, source = load_wordlist(str(path))
    assert words == ["api", "dev", "prod"]
    assert "3 prefixes" in source


def test_empty_file_falls_back(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("\n# only comments\n", encoding="utf-8")
    words, _source = load_wordlist(str(path))
    assert words == list(DEFAULT_WORDLIST)
