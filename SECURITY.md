# Security Policy

## Reporting a Vulnerability

We take the security of this project seriously. If you discover a security vulnerability, please report it responsibly by opening a private security advisory on GitHub or contacting the maintainers directly. Please do not open public issues for sensitive vulnerabilities until a fix has been coordinated.

---

## Security Advisories

### GH-001: Unauthenticated Streamable HTTP Transport and Insecure Default Bind (Fixed)

- **Date:** September 2026
- **Reported By:** Shiqiang Chen (GitHub Issue #1)
- **Severity:** High
- **Affects:** Streamable HTTP transport (`/mcp`) in versions <= 0.1.0

#### Description

A vulnerability report confirmed that the Streamable HTTP transport at `/mcp` lacked transport-level authentication. Anyone capable of reaching port 8000 could invoke all exposed tools without credentials, including write operations such as `create_requisition`. Furthermore, the server defaulted to binding on `0.0.0.0`, exposing the unauthenticated transport across all network interfaces by default.

While the approval token mechanism (`approve_pending_requisition`) and the admin REST routes (`/admin/*`) were properly guarded, the MCP tool execution surface itself was unauthenticated.

#### Resolution

1. **Transport-Level Authentication (`MCP_API_KEY`):**
   - Added `MCPAuthMiddleware` to protect the `/mcp` transport.
   - Requires client requests to supply credentials via `Authorization: Bearer <MCP_API_KEY>` or `X-MCP-API-Key: <MCP_API_KEY>`.
   - Comparison uses timing-safe constant-time equality checks (`secrets.compare_digest`).
   - Fails closed with HTTP 500 (`Server configuration error: MCP_API_KEY not set`) if the environment variable is unset, matching the existing project pattern.

2. **Safe Loopback Default Bind:**
   - Changed the default server bind host from `0.0.0.0` to `127.0.0.1` (loopback-only).
   - Operators running inside containers (Docker) or behind reverse proxies must explicitly opt in by setting `MCP_HOST=0.0.0.0`.

3. **Stdio Isolation:**
   - The local `stdio` transport pipe (used by Claude Desktop) remains unaffected by `MCP_API_KEY`. Because `stdio` is a direct operating system inter-process pipe without network exposure, it does not require network credentials.

4. **Credential Separation:**
   - `MCP_API_KEY` is strictly isolated from `ADMIN_API_KEY`. Having one credential does not grant access to the other surface.

#### Acknowledgments

We thank **Shiqiang Chen** for finding and responsibly disclosing this vulnerability.
