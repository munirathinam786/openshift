# Changelog

## 0.3.0 — Unreleased

### Functionality
- Prompt template library with 5 personas (default, incident_commander, finops_analyst, security_auditor, platform_engineer)
- Token usage tracking (prompt/completion/total) per run
- Run tagging and filtering
- Batch chat endpoint (`POST /chat/batch`)
- Data retention enforcement (`POST /admin/retention`)
- CSV export for run history (`GET /history/export`)
- Graceful shutdown with in-flight request draining

### Platform Tools
- ACM certificate listing
- Route 53 health checks
- SSM Automation execution history
- OpenShift cluster health events
- Trusted Advisor check results
- Service Quotas lookup
- IAM credential report with MFA analysis
- Cost Anomaly Detection results
- CodePipeline pipeline status
- CloudWatch composite and anomaly detection alarms

### Security
- Bearer token authentication middleware (optional via `API_KEY`)
- Prompt injection detection with 6 pattern categories
- Security headers (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
- Bounded rate limiter with LRU eviction (max 10k buckets)

### UX / Dashboard
- Toast notification system for real-time events
- Prompt history with localStorage autocomplete (last 50 prompts)
- Keyboard shortcuts: Ctrl+Enter (submit), Escape (clear), Ctrl+/ (focus)
- WebSocket event notifications for run completion
- Shareable dashboard URLs via query params
- Run comparison view (up to 4 runs side-by-side)
- Shared 3D React operator shell with page-specific accents, section-jump links, feature decks, and persistent theme/density/motion controls
- New operator workspaces for Watchlists, Posture Radar, and Drift Diff
- FinOps workspace report export flow with browser-side PowerPoint and PDF generation plus clearer prerequisite messaging
- Richer workspace metadata and navigation across Console, History, Troubleshooting, LLM Utilization, Tool Drilldown, and FinOps pages

### API / Platform Workflows
- Saved investigations API (`/investigations`) for reusable prompt packs
- Watchlists API (`/watchlists`) with manual fan-out execution across regions and optional role assumptions
- Platform sweep API (`/platform/sweep`) for cross-region and cross-account inspection packs
- History compare API (`/history/compare`) for run-to-run drift analysis
- Direct FastAPI redirect routes for the new operator pages, including `finops-console.html`

### FinOps Reliability
- Prompt manifest narrowing to required tools so large FinOps runs avoid oversized system prompts
- Updated FinOps browser client to use the current `/chat` runtime contract and persisted `/finops/queue` API
- Improved FinOps route handling and export-button UX so the workspace no longer appears broken before a report exists

### Documentation
- Expanded source walkthroughs in `docs/code-runtime.md` and `docs/api-reference.md` to explain the new operator pages, shell features, exports, and APIs
- Refreshed service coverage and generated site artifacts to match the latest authored source

### Operations
- Prometheus-compatible `/metrics` endpoint
- Configurable context window and temperature override
- New `.env.example` variables for v0.3.0 settings
- `Makefile` with common development commands

### Developer Experience
- `Makefile` with install, dev, test, lint, fmt, docs, build, clean targets
- Updated `.env.example` with all new configuration options
- New test suites: `test_api.py`, `test_middleware.py`

## 0.2.0

- Initial public release with core SRE agent, 22 OpenShift tools, troubleshooting workflows, FinOps module, and MkDocs dashboard.
