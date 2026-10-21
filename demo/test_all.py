"""End-to-end check of every tool against the simulated probes.

Usage: python3 demo/test_all.py [base_url]    (default http://localhost:5435/api)
Needs only the standard library. Exit code 1 if any check fails.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5435/api").rstrip("/")
OK_PROBE, OK_PROBE2, DOWN_PROBE = "192.0.2.11", "192.0.2.21", "192.0.2.99"
results = []


def get(path, timeout=30):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read().decode()


def get_safe(path):
    try:
        return get(path)
    except urllib.error.HTTPError:
        return "HTTP-ERROR"


def post(path, body, timeout=60):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode()


def status(path, body=None):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode() if body is not None else None,
                                 {"Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req, timeout=15).status
    except urllib.error.HTTPError as e:
        return e.code


def check(name, cond, detail=""):
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + detail[:300].replace("\n", " | ")))


def result_of(filename, probe, wait_for, tries=40):
    text = ""
    for _ in range(tries):
        text = get(f"/a02_opening_apache_on_golden_eye_server/{urllib.parse.quote(filename)}/{probe}")
        if wait_for in text:
            return text
        time.sleep(0.5)
    return text


def sse(path, body=None):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode() if body else None,
                                 {"Content-Type": "application/json"})
    out = []
    with urllib.request.urlopen(req, timeout=90) as r:
        for line in r:
            line = line.decode().strip()
            if line.startswith("data:"):
                out.append(line[5:].strip())
    return out


# ---- probe lists (axios + DB)
probes = json.loads(get("/axios_paping_server_ip/CT"))
check("probe list CT returns probes", len(probes) >= 1, str(probes))
check("probe by city", "server_private_ip" in get("/axios_show_which_probe_for_webpaping/Shanghai%20(demo)") or
      "ge_server_private_ip" in get("/axios_show_which_probe_for_webpaping/Shanghai%20(demo)"))
check("c10 list", len(json.loads(get("/another_version_axios_paping_server_ip/CT"))) >= 1)

# ---- tcping (paping)
f = get(f"/a01_action_paping_to_ge_probes/www.example.com/443/5/{OK_PROBE}")
t = result_of(f, OK_PROBE, "Failed=") if "error" not in f else f
check("tcping open port: 5 successes", "Connected=5" in t and "Failed=0" in t, f + " " + t)
f = get(f"/a01_action_paping_to_ge_probes/www.example.com/12345/3/{OK_PROBE}")
t = result_of(f, OK_PROBE, "Failed=")
check("tcping closed port: all fail", "Connected=0" in t and "time out" in t, t)
f = get(f"/a01_action_paping_to_ge_probes/service-down.example.com/443/3/{OK_PROBE}")
t = result_of(f, OK_PROBE, "Failed=")
check("tcping dead host: all fail", "Connected=0" in t and "Failed=3" in t, t)
f = get(f"/a01_action_paping_to_ge_probes/www.example.com/443/3/{DOWN_PROBE}")
check("tcping offline probe: clear error", f.startswith("error"), f)

# ---- mtr
f = get(f"/b01_do_mtr_to_ge_probes/www.example.com/443/{OK_PROBE}")
t = result_of(f, OK_PROBE, "---MTR_COMPLETE---")
check("mtr: header, hops, marker", "HOST " in t and "1.|--" in t and "---MTR_COMPLETE---" in t, f + t)
f = get(f"/b01_do_mtr_to_ge_probes/nxdomain.example.com/443/{OK_PROBE}")
t = result_of(f, OK_PROBE, "---MTR_COMPLETE---")
check("mtr unresolvable host reports failure", "Failed to resolve" in t, t)
f = get(f"/b01_do_mtr_to_ge_probes/www.example.com/443/{DOWN_PROBE}")
check("mtr offline probe: clear error", f.startswith("error"), f)

# ---- dig
f = get(f"/c01_do_dig_to_ge_probes/www.example.com/{OK_PROBE}")
t = result_of(f, OK_PROBE, "MSG SIZE")
check("dig: ANSWER SECTION", "ANSWER SECTION" in t and "NOERROR" in t, f + t)
f = get(f"/c01_do_dig_to_ge_probes/nxdomain.example.com/{OK_PROBE}")
t = result_of(f, OK_PROBE, "MSG SIZE")
check("dig NXDOMAIN", "NXDOMAIN" in t, t)

# ---- curl (POST)
body = {"probe_ip": OK_PROBE, "getting_the_ip_or_url_from_vuex": "http://www.example.com/",
        "ip_for_hostfile_from_vuex": "", "url_for_hostfile_from_vuex": "",
        "getting_the_port_from_vuex": "HTTP1.1", "getting_the_tls_version_from_vuex": "Auto"}
f = post("/d01_do_curl_to_ge_probes", body)
t = result_of(f, OK_PROBE, "HTTP/1.1 200")
check("curl http->https redirect then 200", "301" in t and "HTTP/1.1 200" in t, f + t)
body.update(getting_the_port_from_vuex="HTTP2", getting_the_ip_or_url_from_vuex="https://www.example.com/")
f = post("/d01_do_curl_to_ge_probes", body)
t = result_of(f, OK_PROBE, "HTTP/2 200")
check("curl HTTP2", "HTTP/2 200" in t, f + t)
body.update(getting_the_ip_or_url_from_vuex="https://www.example.com/status/503", getting_the_port_from_vuex="HTTP1.1")
f = post("/d01_do_curl_to_ge_probes", body)
t = result_of(f, OK_PROBE, "503")
check("curl 503", "503" in t, t)
body.update(getting_the_ip_or_url_from_vuex="https://nxdomain.example.com/")
f = post("/d01_do_curl_to_ge_probes", body)
t = result_of(f, OK_PROBE, "Could not resolve host")
check("curl unresolvable host", "Could not resolve host" in t, t)
body.update(getting_the_ip_or_url_from_vuex="https://service-down.example.com/")
f = post("/d01_do_curl_to_ge_probes", body)
t = result_of(f, OK_PROBE, "(28)", tries=120)
check("curl timeout", "(28)" in t, t)
body.update(getting_the_ip_or_url_from_vuex="https://www.example.com/", ip_for_hostfile_from_vuex="203.0.113.77",
            url_for_hostfile_from_vuex="www.example.com")
f = post("/d01_do_curl_to_ge_probes", body)
t = result_of(f, OK_PROBE, "HTTP/1.1 200")
check("curl with hosts-file override pings the override IP", "203.0.113.77" in t and "HTTP/1.1 200" in t, t)
body["probe_ip"] = DOWN_PROBE
check("curl offline probe: clear error", post("/d01_do_curl_to_ge_probes", body).startswith("error"))
check("curl without probe_ip -> 400", status("/d01_do_curl_to_ge_probes", {}) == 400)

# ---- httping
f = get(f"/e01_http_ping/www.example.com/{OK_PROBE}/https")
t = result_of(f, OK_PROBE, "round-trip")
check("httping: connects, stats", "connected to" in t and "round-trip" in t, f + t)
f = get(f"/e01_http_ping/service-down.example.com/{OK_PROBE}/http")
t = result_of(f, OK_PROBE, "20 connects", tries=120)
check("httping dead host: timeouts", "0 ok" in t and "100.00% failed" in t, t)

# ---- customized command
for cmd, want in (("ping -c 2 www.example.com", "2 packets transmitted"), ("dig www.example.com", "ANSWER SECTION"),
                  ("nslookup www.example.com", "Address"), ("curl -I https://www.example.com", "HTTP/1.1 200"),
                  ("uptime", "load average"), ("nosuchtool --x", "not found")):
    f = get("/e01_action_customized_command?" + urllib.parse.urlencode({"cmd": cmd, "ip": OK_PROBE}))
    t = result_of(f, OK_PROBE, want)
    check(f"custom command: {cmd}", want in t, f + t)
check("custom command offline probe", get("/e01_action_customized_command?" + urllib.parse.urlencode(
    {"cmd": "uptime", "ip": DOWN_PROBE})).startswith("error"))
check("custom command missing args -> 400", status("/e01_action_customized_command") == 400)

# ---- SSE single
for path, want in ((f"/sse/tcping/www.example.com/443/4/{OK_PROBE}", "Failed"),
                   (f"/sse/mtr/www.example.com/443/{OK_PROBE}", "COMPLETE"),
                   (f"/sse/dig/www.example.com/{OK_PROBE}", "COMPLETE")):
    ev = sse(path)
    check(f"SSE {path.split('/')[2]}: events then completion", len(ev) >= 1 and any(want in e for e in ev), str(ev[-2:]))
ev = sse(f"/sse/tcping/www.example.com/443/4/{DOWN_PROBE}")
check("SSE tcping offline probe: error event", any("error" in e.lower() for e in ev), str(ev))

# ---- SSE batch
probes_b = [OK_PROBE, OK_PROBE2, DOWN_PROBE]
ev = [json.loads(e) for e in sse("/sse/batch/tcping", {"target": "www.example.com", "port": 443, "count": 4, "probes": probes_b})]
done = {e.get("probe_ip") for e in ev if e.get("complete")}
check("batch tcping: every probe completes (incl. offline)", done == set(probes_b), str(done))
check("batch tcping: online probes got data", all(any("Connected" in e.get("data", "")
                                                      for e in ev if e.get("probe_ip") == p) for p in (OK_PROBE, OK_PROBE2)))
ev = [json.loads(e) for e in sse("/sse/batch/mtr", {"target": "www.example.com", "port": 443, "probes": probes_b})]
done = {e.get("probe_ip") for e in ev if e.get("complete")}
check("batch mtr: every probe completes", done == set(probes_b), str(done))
check("batch mtr: hops present", any("1.|--" in e.get("data", "") for e in ev))

# ---- whitelist CRUD + check
row = json.loads(post("/api/whitelist", {"condition_type": "success", "condition_pattern": "HTTP/[0-9.]+ 204",
                                         "condition_name": "sim test 204", "description": "t", "is_enabled": True}))
rid = row.get("id") or row.get("condition", {}).get("id")
check("whitelist create", rid is not None, str(row))
lst = json.loads(get("/api/whitelist"))
check("whitelist list contains built-ins + new", len(lst) >= 4, str(len(lst)))
r = json.loads(post("/api/check_whitelist", {"content": "HTTP/1.1 200 OK\r\n", "country": "CT"}))
check("whitelist check 200 -> success", "success" in json.dumps(r).lower(), str(r))
r = json.loads(post("/api/check_whitelist", {"content": "HTTP/1.1 503 Service Unavailable\r\n", "country": "CT"}))
check("whitelist check 5xx -> failure", "fail" in json.dumps(r).lower(), str(r))
if rid is not None:
    req = urllib.request.Request(BASE + f"/api/whitelist/{rid}", method="DELETE")
    urllib.request.urlopen(req, timeout=10)
    check("whitelist delete", all(x["id"] != rid for x in json.loads(get("/api/whitelist"))))

# ---- update probe public IP (myip.txt of the simulated probe)
pid = probes[0]["id"]
r = json.loads(post(f"/update_probe_public_ip/{pid}", {}))
check("update probe public IP from simulated myip.txt", r.get("success") is True, str(r))

# ---- safety: bad probe names must not touch the filesystem outside SIM_DIR
for bad in ("..", "x..y", "a%2Fb"):
    r = status(f"/a02_opening_apache_on_golden_eye_server/passwd/{bad}")
    t = get_safe(f"/a01_action_paping_to_ge_probes/www.example.com/443/1/{bad}")
    check(f"bad probe name {bad!r} rejected", t.startswith("error") or t == "HTTP-ERROR", t)

# ---- input validation and stream edge cases
check("bad port -> 400", status("/a01_action_paping_to_ge_probes/www.example.com/abc/3/192.0.2.11") == 400)
check("count 0 -> 400", status("/a01_action_paping_to_ge_probes/www.example.com/443/0/192.0.2.11") == 400)
check("target with ';' -> 400", status("/sse/tcping/a;b/443/3/192.0.2.11") == 400)
check("empty batch -> 400", status("/sse/batch/tcping", {"target": "x", "probes": []}) == 400)
ev = [json.loads(e) for e in sse("/sse/batch/tcping", {"target": "www.example.com", "port": 443, "count": 2, "probes": [OK_PROBE, OK_PROBE]})]
check("batch with duplicate probes finishes", any(e.get("all_complete") for e in ev), str(ev[-1:]))
ev = sse(f"/sse/tcping/host404.example.com/443/3/{OK_PROBE}")
check("target containing 404 still streams the paping lines", any("Connected=" in e or "Failed=" in e for e in ev), str(ev)[-200:])

# ---- every ISP button has probes, and a batch run works for each
for isp in ("CT", "CU", "CM", "VN", "INDO", "Malaysia", "Cambodia", "TH", "KR"):
    pl = json.loads(get(f"/axios_show_which_host_isp_for_webpaping/{isp}"))
    ips = [x["ge_server_private_ip"] for x in pl if x["ge_server_private_ip"] != DOWN_PROBE]
    check(f"ISP {isp}: probe list not empty", len(ips) >= 1, str(pl))
    ev = [json.loads(e) for e in sse("/sse/batch/tcping", {"target": "www.example.com", "port": 443, "count": 2, "probes": ips})]
    check(f"ISP {isp}: batch tcping completes", {e.get("probe_ip") for e in ev if e.get("complete")} == set(ips))

# ---- F5 BigIP cookie decoding + simulated LTM config
body.update(probe_ip=OK_PROBE, getting_the_ip_or_url_from_vuex="https://f5-app.example.com/", ip_for_hostfile_from_vuex="",
            url_for_hostfile_from_vuex="")
f = post("/d01_do_curl_to_ge_probes", body)
t = result_of(f, OK_PROBE, "Set-Cookie")
check("curl to an f5 host shows the BigIP cookie", "oneapi=838992064.20480.0000" in t, t)
r = json.loads(post("/api/check_ltm_config", {"content": t}))
check("LTM config check decodes cookie and matches 192.0.2.50", r.get("status") == "success" and "192.0.2.50" in json.dumps(r), str(r)[:300])

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
