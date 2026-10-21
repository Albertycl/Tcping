# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flask web application for network diagnostic tools (tcping, mtr, dig, curl, http ping, custom commands) run against probes. The probes are simulated by `utils/probe_sim.py`; see the root `CLAUDE.md`.

## Architecture

- **Main Application**: `main_for_paping_tcptrace.py` - Flask app entry point with blueprint registration
- **Database Models**: `model.py` - SQLAlchemy models for probe data
- **Configuration**: `config.py` - reads `DATABASE_URL` from the environment
- **Blueprints**: `blueprint_paping/` - one module per tool (paping, mtr, dig, curl, http_ping, customized_command, axios, whitelist, sse, show-result)
- **Utils**: `utils/probe_sim.py`, `utils/probe_http.py`, `utils/tcp_check.py`

## Running

```bash
pip install -r requirements.txt
DATABASE_URL=... gunicorn -k gthread -b 0.0.0.0:5100 main_for_paping_tcptrace:app
```

In practice use `docker compose up -d --build` from the repo root.

## Key Dependencies
- Flask with SQLAlchemy and CORS support
- Requests for HTTP operations
- Gunicorn for serving, PyMySQL for the database
