# Tcping: full details

[Back to the short README](../README.md)

**Live demo:** https://tcping.albertycliu.xyz (no login on purpose, for the demo; the probes are simulated)

A web tool that runs network diagnostics (TCP ping, MTR / traceroute, dig, curl, HTTP ping and custom commands) from a list of probe servers in different countries and ISPs, and shows the results live in the browser.

> **Demo only.** The original probe servers no longer exist, so the probes are **simulated** by `backend/utils/probe_sim.py`. It reads the command, never runs it, and writes believable output. Nothing here talks to a real probe or a real SSH server.

## What it is and why it matters for SRE

- **Who uses it:** a network or support engineer who wants to see "can users in ISP X reach host Y?" from several vantage points at once.
- **How it works:** the user picks probes (grouped by ISP, for example CT, CU, CM, VN, INDO, KR), a tool and a target. The backend starts the command on every probe in parallel and streams the output back with Server-Sent Events (SSE). A whitelist of response patterns, including decoding of F5 BigIP persistence cookies, marks curl results as expected or not.
- **SRE skills shown:** containers (multi-stage Docker builds), GitOps (manifests in a separate repo), CI/CD (GitHub Actions to GHCR to Argo CD), Kubernetes on K3s, rollback with `git revert`, streaming through a reverse proxy (SSE needs `proxy_buffering off`), and running a stateful database in the cluster.
- **Deliberately simple:** one backend replica, no authentication, no metrics endpoint. See "Known limits".

Simulated scenarios: put one of these words in the target host name and the simulator behaves that way: `down`, `timeout`, `blocked` (no answer), `flaky` (packet loss), `slow`, `nxdomain`, `invalid` (DNS failure). One probe in the seed data (`192.0.2.99`) is always offline.

## Architecture

| Part | Tech | Notes |
| --- | --- | --- |
| frontend | Vue 2 + Vuetify + Vuex, served by nginx | History-mode router. nginx proxies `/api/` to the backend with the prefix removed and buffering off (needed for SSE). |
| backend | Flask + Flask-SQLAlchemy, gunicorn (gthread) | One module per tool in `backend/blueprint_paping/`. Batch endpoints `/sse/batch/tcping` and `/sse/batch/mtr` validate their input and return 400 with a message. |
| probe simulator | `backend/utils/probe_sim.py` | Same calls as the old SSH client, writes result files into `SIM_DIR`. |
| database | MariaDB 11.1 | Tables: probes, ISP probe list and whitelist. Seeded from `demo/seed_demo_data.sql` with documentation-range IPs (RFC 5737). |

Request flow: browser -> nginx (`/api/...`) -> Flask -> simulator writes result files -> the SSE stream (or polling) reads them -> browser. Probe lists and whitelist come from MariaDB.

Deployment manifests live in [`Albertycl/Gitops-apps`](https://github.com/Albertycl/Gitops-apps) under `manifests/tcping/`.

## Install and run

### a) Locally with Docker Compose

Prerequisites: Docker with the Compose plugin.

```
cp .env.example .env     # set MYSQL_APP_PASSWORD (any value without special characters)
docker compose -f docker-compose.standalone.yml up --build
```

Open http://localhost:5435 (change the port with `FRONTEND_PORT` in `.env`). The database starts empty and loads `demo/seed_demo_data.sql` on its first start. Stop with `docker compose -f docker-compose.standalone.yml down` (add `-v` to delete the database volume).

`docker-compose.yml` is the variant used on the author's server: it needs an existing MariaDB container and an external Docker network (`netdiag_default`), so strangers should use the standalone file.

Check that everything works (end-to-end checks against the API):

```
python3 demo/test_all.py http://localhost:5435/api
```

### b) On Kubernetes (K3s) with Argo CD

1. One-time bootstrap of Argo CD (done once for all apps), from a clone of `gitops-apps`: `kubectl apply -f argocd/root-app.yaml`. It watches `apps/`, and `apps/tcping.yaml` points at `manifests/tcping/`.
2. After the first sync Argo CD has created the namespace `tcping`. Create the Secret by hand, because secrets are never in Git. The value must not contain characters that need URL escaping:
   `kubectl -n tcping create secret generic tcping-db --from-literal=password="$(openssl rand -hex 16)"` (key: `password`).
3. After the first CI run, set the two GHCR packages `tcping-backend` and `tcping-frontend` to public (the pods have no `imagePullSecrets`, so they show ImagePullBackOff until then).
4. Check: `kubectl get applications -n argocd` shows `tcping` as Synced and Healthy, and `kubectl get pods -n tcping` shows mariadb, backend and frontend Ready.

## CI/CD and rollback

Push to `main` runs `.github/workflows/ci.yml`:

1. **test** (also on pull requests): backend import check, frontend production build.
2. **build**: build and push two images to GHCR (`ghcr.io/albertycl/tcping-backend` and `tcping-frontend`), tagged with the commit SHA and `latest`.
3. **update-gitops**: run `kustomize edit set image` in `manifests/tcping/` of `gitops-apps` and push with a deploy key (repo secret `GITOPS_DEPLOY_KEY`). Argo CD then syncs.

Rollback: `git revert` the "tcping: deploy <sha>" commit in `gitops-apps`. Do not use `kubectl rollout undo`, because Argo CD self-heal puts the old state back.

## Monitoring and known limits

- **Monitoring:** no metrics or alerts for this app yet (no `/metrics`). Kubernetes health checks (readiness probes) cover all three pods. The cluster also injects OpenTelemetry tracing into the backend (`manifests/tcping/instrumentation.yaml`), and the browser can send spans through the `/otlp/` route of nginx to a collector in the cluster; the collector itself is not part of this repo.
- **Known limits (demo):**
  - Probes are simulated, so the numbers are made up.
  - No authentication: the whitelist write routes and the UI are open. CORS is `*`.
  - `DevConfig` (`DEBUG=True`) is the only config the app loads, also in the container.
  - If the backend is down the page stays blank and shows no alert.
  - Result files are kept in the container's `/tmp` and are lost on restart.
  - One backend replica.
