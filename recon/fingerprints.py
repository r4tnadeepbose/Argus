"""Subdomain-takeover fingerprints.

Maps a CNAME suffix to the service that owns it and to page markers that
indicate the resource behind that CNAME is unclaimed.
"""

from __future__ import annotations

from typing import TypedDict


class ServiceFingerprint(TypedDict):
    service: str
    markers: list[str]


TAKEOVER_SERVICES: dict[str, ServiceFingerprint] = {
    "github.io": {"service": "GitHub Pages", "markers": [
        "there isn’t a github pages site here",
        "there isn't a github pages site here",
        "for root urls (like http://example.com/) you must provide an index.html file"]},
    "amazonaws.com": {"service": "AWS S3", "markers": [
        "nosuchbucket", "the specified bucket does not exist"]},
    "herokuapp.com": {"service": "Heroku", "markers": ["no such app"]},
    "herokudns.com": {"service": "Heroku", "markers": ["no such app"]},
    "cloudfront.net": {"service": "CloudFront", "markers": [
        "error: the request could not be satisfied"]},
    "fastly.net": {"service": "Fastly", "markers": ["fastly error: unknown domain"]},
    "azurewebsites.net": {"service": "Azure App Service", "markers": ["404 web site not found"]},
    "cloudapp.azure.com": {"service": "Azure VM", "markers": []},
    "trafficmanager.net": {"service": "Azure Traffic Manager", "markers": []},
    "blob.core.windows.net": {"service": "Azure Blob", "markers": ["blobnotfound"]},
    "netlify.app": {"service": "Netlify", "markers": ["not found - request id"]},
    "netlify.com": {"service": "Netlify", "markers": ["not found - request id"]},
    "surge.sh": {"service": "Surge", "markers": ["project not found"]},
    "bitbucket.io": {"service": "Bitbucket", "markers": ["repository not found"]},
    "readthedocs.io": {"service": "Read the Docs", "markers": ["unknown to read the docs"]},
    "wordpress.com": {"service": "WordPress", "markers": ["doesn’t exist", "doesn't exist"]},
    "myshopify.com": {"service": "Shopify", "markers": [
        "sorry, this shop is currently unavailable"]},
    "zendesk.com": {"service": "Zendesk", "markers": ["help center closed"]},
    "statuspage.io": {"service": "Statuspage", "markers": ["this page is not yet available"]},
    "pantheonsite.io": {"service": "Pantheon", "markers": ["the gods are wise"]},
    "tumblr.com": {"service": "Tumblr", "markers": ["there's nothing here"]},
    "ghost.io": {"service": "Ghost", "markers": ["domain error"]},
    "webflow.io": {"service": "Webflow", "markers": [
        "the page you are looking for doesn’t exist",
        "the page you are looking for doesn't exist"]},
    "uservoice.com": {"service": "UserVoice", "markers": [
        "this uservoice subdomain is currently available"]},
    "helpscoutdocs.com": {"service": "Help Scout", "markers": [
        "no settings were found for this company"]},
    "teamtailor.com": {"service": "Teamtailor", "markers": ["this site is no longer available"]},
    "launchrock.com": {"service": "LaunchRock", "markers": [
        "it looks like you may have taken a wrong turn"]},
    "digitaloceanspaces.com": {"service": "DigitalOcean Spaces", "markers": ["nosuchbucket"]},
    "storage.googleapis.com": {"service": "Google Cloud Storage", "markers": ["nosuchbucket"]},
    "firebaseapp.com": {"service": "Firebase", "markers": ["site not found"]},
    "web.app": {"service": "Firebase", "markers": ["site not found"]},
    "vercel.app": {"service": "Vercel", "markers": ["deployment could not be found"]},
    "pages.dev": {"service": "Cloudflare Pages", "markers": ["project not found"]},
    "fly.dev": {"service": "Fly.io", "markers": []},
}

# Longest suffix first so e.g. ``blob.core.windows.net`` wins over a shorter match.
_SUFFIXES = sorted(TAKEOVER_SERVICES, key=len, reverse=True)


def service_for_cname(cname: str) -> ServiceFingerprint | None:
    """Return the service fingerprint for *cname*, or ``None``.

    A CNAME matches a service when it equals the suffix or ends with
    ``"." + suffix`` (so ``user.github.io`` matches ``github.io``).
    """
    cname = cname.strip().rstrip(".").lower()
    if not cname:
        return None
    for suffix in _SUFFIXES:
        if cname == suffix or cname.endswith("." + suffix):
            return TAKEOVER_SERVICES[suffix]
    return None
