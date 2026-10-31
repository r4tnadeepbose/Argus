# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x | Yes |
| 0.x | No |

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Instead, use the private security advisory feature of the repository hosting
platform (for GitHub: *Security → Report a vulnerability*), or contact the
maintainer through the same platform. Include:

- A description of the issue and its impact.
- Steps to reproduce (a minimal harness if possible).
- The version/commit and your operating system.

You will receive an acknowledgement as soon as possible, and an update when the
issue is triaged.

## Scope

In scope:

- Command injection or argument confusion in subprocess calls.
- Path traversal or unsafe file writes in `recon/state.py`.
- Crashes triggered by hostile tool output (JSON/stdout parsing).
- Credential or secret leakage from this repository.

Out of scope:

- Findings that require a compromised local machine.
- Vulnerabilities in `subfinder`, `httpx`, `dnsx`, Telegram or other third-party
  services.
- Reports about scanning third-party domains: using this tool without
  authorization is a violation of the acceptable-use policy, not a
  vulnerability.

## Safe harbour

Good-faith research on this codebase, using your own test targets, is welcome.
Do not test the tool against systems you do not own or have permission to test.
