from recon.fingerprints import service_for_cname


def test_github_pages():
    assert service_for_cname("user.github.io")["service"] == "GitHub Pages"


def test_aws_s3():
    assert service_for_cname("bucket.s3.amazonaws.com")["service"] == "AWS S3"


def test_longest_suffix_wins():
    assert service_for_cname("acct.blob.core.windows.net")["service"] == "Azure Blob"
    assert service_for_cname("x.storage.googleapis.com")["service"] == "Google Cloud Storage"


def test_normalises_case_and_trailing_dot():
    assert service_for_cname("User.GitHub.IO.")["service"] == "GitHub Pages"


def test_rejects_unrelated_suffix():
    # Same letters, but not a real subdomain boundary.
    assert service_for_cname("notgithub.io") is None
    assert service_for_cname("example.com") is None
    assert service_for_cname("myweb.app") is None


def test_accepts_service_apex_and_subdomain():
    assert service_for_cname("web.app")["service"] == "Firebase"
    assert service_for_cname("site.web.app")["service"] == "Firebase"
