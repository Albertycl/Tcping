# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack network diagnostics platform for running TCP ping, MTR/traceroute, dig, curl, HTTP ping and custom commands against distributed network probes. The original SSH probe servers no longer exist, so the probes are simulated (see "Probe simulation").

## Architecture

### Backend (Flask)
**Location:** `backend/`

- **Entry Point:** `main_for_paping_tcptrace.py` - Flask app with blueprint registration
- **Models:** `model.py` - SQLAlchemy models for probes (`b11_huck_ge_probes`) and whitelist (`WhitelistCondition`)
- **Blueprints:** `blueprint_paping/` - one module per tool:
  - `paping_blueprint.py` - TCP ping
  - `mtr_blueprint.py` - MTR/traceroute
  - `dig_blueprint.py` - DNS lookups
  - `curl_blueprint.py` - HTTP/HTTPS testing
  - `http_ping_blueprint.py` - HTTP ping
  - `customized_command_blueprint.py` - custom commands
  - `whitelist_blueprint.py` - response whitelist management with F5 BigIP cookie decoding
  - `sse_blueprint.py` - Server-Sent Events for single and batch probe execution
- **Utils:** `utils/`
  - `probe_sim.py` - simulated probe servers (SSH client look-alike, tool emulators, result files)
  - `probe_http.py` - reads simulated result files where the code used to fetch them over HTTP
  - `tcp_check.py` - probe reachability pre-check (asks the simulator)

### Frontend (Vue.js)
**Location:** `frontend_webtcping/`

- **Components:** `src/components/`
  - `landing_page/tcping/` - page-level components for each tool
  - `components_within_the_page/` - per-probe result components (e.g., `curl_for_each_probe.vue`)
- **State:** `src/store/index.js` - Vuex store for probe selection, batch results, SSE state
- **Router:** `src/router/index.js` - routes with lazy loading

### Database
- MariaDB database `tcping`, set by `DATABASE_URL` in `.env` (see `.env.example`). Never commit real credentials.
- `demo/seed_demo_data.sql` loads demo probes and whitelist conditions.

## Probe simulation

- `probe_sim.SSHClient` has the same calls the code used with paramiko, but it never runs the command. It reads the command string, produces plausible output and writes it to `SIM_DIR` files gradually.
- The scenario comes from words in the target host: `down`/`timeout`/`blocked` (no answer), `flaky` (packet loss), `slow`, `nxdomain`/`invalid` (DNS failure).
- Env: `SIM_DIR`, `SIM_INTERVAL`, `SIM_DOWN_PROBES` (default `192.0.2.99`, a probe that is unreachable).
- Do not reintroduce real SSH, Globalping or IP-to-location (ASN) lookups.

## Development Commands

```bash
cp .env.example .env
docker compose up -d --build     # frontend on :5435, API through its /api proxy
```

Frontend alone: `cd frontend_webtcping && npm install && npm run serve`.

## Key Patterns

### Whitelist System
- Checks curl responses against regex patterns in the whitelist table
- Supports country-specific rules (ISP codes: CT, CU, CM for China)
- F5 BigIP cookie decoding: extracts server IPs from cookies like `oneapi=1613238026.20480.0000`

### Batch Execution (SSE)
- Frontend subscribes to `/sse/batch/*` endpoints
- Backend runs probes in parallel and streams results
- Vuex tracks `probeResults`, `probeCompleted`, `batchInProgress` per tool
