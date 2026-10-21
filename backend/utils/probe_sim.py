"""Simulated probe servers.

The real probes (reached over SSH, results served by Apache on :8787) no longer exist.
This module replaces them: SSHClient has the same shape as an SSH client, but it never
connects anywhere and never runs a command. It only reads the command string, produces
believable output for the supported tools, and writes it to files in SIM_DIR.
fetch_result() plays the role of the HTTP GET to the probe's Apache.

Scenarios are chosen by words in the target host name (documentation-range IPs only):
  down / timeout / blocked  -> TCP port closed, ping 100% loss
  flaky                     -> about 30% loss
  slow                      -> high latency
  nxdomain / invalid        -> DNS lookup fails
A probe listed in SIM_DOWN_PROBES (comma separated, default 192.0.2.99) is unreachable.
"""
import hashlib
import os
import random
import re
import shlex
import threading
import time
from datetime import datetime

SIM_DIR = os.environ.get("SIM_DIR", "/tmp/probe_sim")
INTERVAL = float(os.environ.get("SIM_INTERVAL", "0.3"))
WEB_ROOT = "/var/www/html/"
F5_DEMO_MEMBER = "192.0.2.50"
F5_DEMO_COOKIE = "oneapi=838992064.20480.0000"  # F5 BigIP encoding of 192.0.2.50:80 (shown for hosts containing "f5")
OPEN_PORTS = {21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995, 3306, 5432, 6379, 8080, 8443}


def _down_probes():
    return {p.strip() for p in os.environ.get("SIM_DOWN_PROBES", "192.0.2.99").split(",") if p.strip()}


def probe_is_up(ip):
    valid = bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]*", ip or "")) and ".." not in ip
    return valid and ip not in _down_probes()


def _h(*parts):
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:12], 16)


def probe_hostname(probe):
    return "sim-probe-" + probe.replace(".", "-")


def probe_public_ip(probe):
    last = probe.split(".")[-1]
    return ("198.51.100." if probe.startswith("192.0.2.") else "203.0.113.") + last


def _scenario(host):
    h = host.lower()
    return {
        "dead": any(w in h for w in ("down", "timeout", "blocked")),
        "flaky": "flaky" in h,
        "slow": "slow" in h,
        "nxdomain": "nxdomain" in h or "invalid" in h,
    }


def _is_ip(s):
    return re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", s or "") is not None


def _resolve(host, hosts):
    if _is_ip(host):
        return host
    if host in hosts:
        return hosts[host]
    if _scenario(host)["nxdomain"] or not re.fullmatch(r"[A-Za-z0-9._-]+", host or "") or "." not in host:
        return None
    n = _h("dns", host)
    pool = ("192.0.2.", "198.51.100.", "203.0.113.")
    return pool[n % 3] + str(1 + (n // 3) % 253)


def _latency(probe, host, port=0):
    base = 4 + _h("probe", probe) % 50
    far = 3 + _h("target", host) % 110
    ms = base + far
    return ms * 6 if _scenario(host)["slow"] else ms


def _count(args, default):
    n = int(_opt(args, "-c", default) or default)
    if not 1 <= n <= 100:
        raise ValueError("count must be 1 to 100")
    return n


def _rtts(probe, host, port, count):
    sc = _scenario(host)
    base = _latency(probe, host, port)
    out = []
    for _ in range(count):
        if sc["dead"] or (sc["flaky"] and random.random() < 0.3):
            out.append(None)
        else:
            out.append(round(max(0.5, random.gauss(base, base * 0.06)), 2))
    return out


def _stats(vals):
    ok = [v for v in vals if v is not None]
    if not ok:
        return None
    avg = sum(ok) / len(ok)
    sd = (sum((v - avg) ** 2 for v in ok) / len(ok)) ** 0.5
    return min(ok), avg, max(ok), sd


# ---------------------------------------------------------------- tools
# Each tool takes (probe, args, hosts) and yields (text, delay_after_seconds).

def _opt(args, flag, default=None):
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    return default


def _positional(args, value_flags=()):
    skip = False
    pos = []
    for a in args:
        if skip:
            skip = False
        elif a in value_flags:
            skip = True
        elif not a.startswith("-"):
            pos.append(a)
    return pos


def tool_ping(probe, args, hosts):
    pos = _positional(args, ("-c", "-W", "-i", "-s", "-t"))
    if not pos:
        yield "ping: usage error: Destination address required\n", 0
        return
    host = pos[0]
    count = _count(args, "4")
    ip = _resolve(host, hosts)
    if not ip:
        yield f"ping: {host}: Name or service not known\n", 0
        return
    yield f"PING {host} ({ip}) 56(84) bytes of data.\n", 0
    rtts = _rtts(probe, host, 0, count)
    for i, r in enumerate(rtts, 1):
        if r is not None:
            yield f"64 bytes from {ip}: icmp_seq={i} ttl={50 + _h('ttl', host) % 14} time={r} ms\n", INTERVAL
    st = _stats(rtts)
    got = sum(1 for r in rtts if r is not None)
    loss = round(100 * (count - got) / count)
    yield f"\n--- {host} ping statistics ---\n", 0
    yield f"{count} packets transmitted, {got} received, {loss}% packet loss, time {(count - 1) * 1000}ms\n", 0
    if st:
        yield f"rtt min/avg/max/mdev = {st[0]:.3f}/{st[1]:.3f}/{st[2]:.3f}/{st[3]:.3f} ms\n", 0


def tool_paping(probe, args, hosts):
    pos = _positional(args, ("-c", "-p", "-t", "-r"))
    if not pos:
        yield "paping: no host given\n", 0
        return
    host = pos[0]
    port = int(_opt(args, "-p", "80") or 80)
    count = _count(args, "4")
    ip = _resolve(host, hosts)
    yield "paping v1.5.5 - Copyright (c) 2011 Mike Lovell\n\n", 0
    if not ip:
        yield f"Unable to resolve {host}\n", 0
        return
    yield f"Connecting to {ip} on TCP port {port}:\n\n", 0
    sc = _scenario(host)
    closed = sc["dead"] or port not in OPEN_PORTS
    vals = [None] * count if closed else _rtts(probe, host, port, count)
    for r in vals:
        if r is None:
            yield "Connection timed out\n", INTERVAL
        else:
            yield f"Connected to {ip}: time={r:.2f}ms protocol=TCP port={port}\n", INTERVAL
    ok = sum(1 for v in vals if v is not None)
    yield "\nConnection statistics:\n", 0
    yield f"\tAttempted = {count}, Connected = {ok}, Failed = {count - ok} ({100 * (count - ok) / count:.2f}%)\n", 0
    st = _stats(vals)
    if st:
        yield "Approximate connection times:\n", 0
        yield f"\tMinimum = {st[0]:.2f}ms, Maximum = {st[2]:.2f}ms, Average = {st[1]:.2f}ms\n", 0


def _hops(probe, host, ip):
    n = 5 + _h("hops", host) % 5
    hops = [("10.%d.0.1" % (_h(probe) % 250), "AS???")]
    asns = [64496, 64497, 64498, 64499, 64500]
    for i in range(1, n - 1):
        a = asns[min(i // 2, len(asns) - 1)]
        hops.append(("198.18.%d.%d" % (_h(probe, host, i) % 250, 1 + _h(host, i) % 250), "AS%d" % a))
    hops.append((ip, "AS%d" % (64500 + _h("dst", host) % 11)))
    return hops


def tool_mtr(probe, args, hosts):
    pos = _positional(args, ("-c", "-m", "-P"))
    if not pos:
        yield "mtr: no host given\n", 0
        return
    host = pos[0]
    count = _count(args, "10")
    ip = _resolve(host, hosts)
    if not ip:
        yield f"Failed to resolve host: {host}: Name or service not known\n", 0
        return
    sc = _scenario(host)
    yield f"Start: {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}\n", 0
    yield f"HOST: {probe_hostname(probe):<22}Loss%   Snt   Last   Avg  Best  Wrst StDev\n", 1.0
    hops = _hops(probe, host, ip)
    total = _latency(probe, host)
    lines = []
    for i, (hip, asn) in enumerate(hops, 1):
        last_hop = i == len(hops)
        if last_hop and sc["dead"]:
            lines.append(f"{i:>3}.|-- {'AS???':<8}{'???':<17}100.0%  {count:>4}   0.0   0.0   0.0   0.0   0.0")
            continue
        base = max(0.4, total * i / len(hops))
        rtts = [round(max(0.2, random.gauss(base, base * 0.08)), 1) for _ in range(count)]
        lost = sum(1 for _ in range(count) if sc["flaky"] and last_hop and random.random() < 0.3)
        st = _stats(rtts)
        loss = 100.0 * lost / count
        lines.append(f"{i:>3}.|-- {asn:<8}{hip:<17}{loss:>5.1f}%  {count:>4}  {rtts[-1]:>5.1f} {st[1]:>5.1f} {st[0]:>5.1f} {st[2]:>5.1f} {st[3]:>5.1f}")
    for ln in lines:
        yield ln + "\n", 0


def tool_traceroute(probe, args, hosts):
    pos = _positional(args)
    host = pos[0] if pos else ""
    ip = _resolve(host, hosts)
    if not ip:
        yield f"traceroute: unknown host {host}\n", 0
        return
    yield f"traceroute to {host} ({ip}), 30 hops max, 60 byte packets\n", 0.5
    total = _latency(probe, host)
    hops = _hops(probe, host, ip)
    for i, (hip, _asn) in enumerate(hops, 1):
        base = max(0.4, total * i / len(hops))
        t = "  ".join(f"{random.gauss(base, base * 0.05):.3f} ms" for _ in range(3))
        yield f" {i}  {hip}  {t}\n", 0


def tool_dig(probe, args, hosts):
    pos = _positional(args)
    host = pos[0] if pos else "."
    rtype = pos[1].upper() if len(pos) > 1 and pos[1].isalpha() else "A"
    ip = _resolve(host, hosts)
    qtime = 3 + _h("q", probe, host) % 60
    head = (f"\n; <<>> DiG 9.18.24-1-Debian <<>> {host}\n;; global options: +cmd\n;; Got answer:\n"
            f";; ->>HEADER<<- opcode: QUERY, status: %s, id: {_h('id', host) % 60000}\n"
            ";; flags: qr rd ra; QUERY: 1, ANSWER: %d, AUTHORITY: 0, ADDITIONAL: 1\n\n"
            ";; OPT PSEUDOSECTION:\n; EDNS: version: 0, flags:; udp: 1232\n"
            f";; QUESTION SECTION:\n;{host}.\t\t\tIN\t{rtype}\n\n")
    tail = (f"\n;; Query time: {qtime} msec\n;; SERVER: 192.0.2.53#53(192.0.2.53) (UDP)\n"
            f";; WHEN: {datetime.now().strftime('%a %b %d %H:%M:%S UTC %Y')}\n;; MSG SIZE  rcvd: %d\n")
    if not ip:
        yield head % ("NXDOMAIN", 0) + "" + tail % 40, 0.3
        return
    if rtype == "A":
        answers = [ip] if _is_ip(host) else [ip] + (["198.51.100.%d" % (1 + _h("a2", host) % 250)] if _h("n", host) % 2 else [])
        body = ";; ANSWER SECTION:\n" + "".join(f"{host}.\t\t300\tIN\tA\t{a}\n" for a in answers)
        yield head % ("NOERROR", len(answers)) + body + tail % (50 + 16 * len(answers)), 0.3
    else:
        yield head % ("NOERROR", 0) + tail % 40, 0.3


def tool_nslookup(probe, args, hosts):
    pos = _positional(args)
    host = pos[0] if pos else ""
    ip = _resolve(host, hosts)
    yield "Server:\t\t192.0.2.53\nAddress:\t192.0.2.53#53\n\n", 0.2
    if not ip:
        yield f"** server can't find {host}: NXDOMAIN\n", 0
    else:
        yield f"Non-authoritative answer:\nName:\t{host}\nAddress: {ip}\n", 0


def tool_curl(probe, args, hosts):
    pos = _positional(args, ("-m", "--tls-max", "--max-time", "-H", "-X", "-o"))
    if not pos:
        yield "curl: try 'curl --help' for more information\n", 0
        return
    url = pos[-1]
    follow = any(a.startswith("-") and not a.startswith("--") and "L" in a for a in args)
    head = any(a.startswith("-") and not a.startswith("--") and "I" in a for a in args)
    http2 = "--http2" in args
    proto = "HTTP/2" if http2 else "HTTP/1.1"
    if "://" not in url:
        url = "http://" + url
    scheme, rest = url.split("://", 1)
    host = re.split(r"[/:?]", rest, 1)[0]
    path = rest[len(host):]
    port_m = re.match(r":(\d+)", path)
    if port_m:
        path = path[len(port_m.group(0)):]
    ip = _resolve(host, hosts)
    sc = _scenario(host)
    if not ip:
        yield f"curl: (6) Could not resolve host: {host}\n", 0
        return
    if sc["dead"]:
        yield "curl: (28) Connection timed out after 10001 milliseconds\n", 2.0
        return
    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    status = 200
    m = re.search(r"/status/(\d{3})", path)
    if m:
        status = int(m.group(1))
    elif "flaky" in host and random.random() < 0.5:
        status = 503
    reasons = {200: "OK", 301: "Moved Permanently", 302: "Found", 404: "Not Found", 500: "Internal Server Error",
               502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout"}

    def block(st, extra):
        line = f"{proto} {st}" + ("" if http2 else f" {reasons.get(st, 'Status')}")
        return line + "\r\n" + "".join(f"{k}: {v}\r\n" for k, v in extra) + "\r\n"

    f5_cookie = [("Set-Cookie", F5_DEMO_COOKIE + "; path=/")] if "f5" in host else []
    if scheme == "http" and follow and not m and ("." in host) and not host.endswith(".local"):
        target = f"https://{host}{path or '/'}"
        yield block(301, [("Server", "sim-nginx"), ("Date", now), ("Location", target), ("Content-Length", "169")]), 0.4
        yield block(status, [("Server", "sim-nginx"), ("Date", now), ("Content-Type", "text/html; charset=utf-8"),
                             ("Content-Length", str(1000 + _h(host) % 5000)), ("Connection", "keep-alive")] + f5_cookie), 0
    else:
        yield block(status, [("Server", "sim-nginx"), ("Date", now), ("Content-Type", "text/html; charset=utf-8"),
                             ("Content-Length", str(1000 + _h(host) % 5000)), ("Connection", "keep-alive")] + f5_cookie), 0.4
    if not head:
        yield f"<html><body>simulated response from {host}</body></html>\n", 0


def tool_httping(probe, args, hosts):
    url = [a for a in args if "://" in a]
    url = url[-1] if url else (_positional(args, ("-c",)) or [""])[-1]
    count = _count(args, "5")
    scheme = url.split("://")[0] if "://" in url else "http"
    host = re.split(r"[/:?]", url.split("://", 1)[-1], 1)[0]
    port = 443 if scheme == "https" else 80
    ip = _resolve(host, hosts)
    if not ip:
        yield f"resolving {host}: Name or service not known\n", 0
        return
    yield f"PING {host}:{port} ({url}):\n", 0
    vals = [None] * count if _scenario(host)["dead"] else _rtts(probe, host, port, count)
    for i, r in enumerate(vals):
        if r is None:
            yield f"timeout receiving reply from {ip}:{port} seq={i}\n", INTERVAL
        else:
            yield f"connected to {ip}:{port} (277 bytes), seq={i} time={r * 2:.2f} ms 200 OK {int(500 + _h(host, i) % 900)}KB/s\n", INTERVAL
    ok = sum(1 for v in vals if v is not None)
    yield f"--- {url} ping statistics ---\n", 0
    yield f"{count} connects, {ok} ok, {100 * (count - ok) / count:.2f}% failed, time {count * 1000}ms\n", 0
    st = _stats([v * 2 if v else v for v in vals])
    if st:
        yield f"round-trip min/avg/max = {st[0]:.1f}/{st[1]:.1f}/{st[2]:.1f} ms\n", 0


def tool_nc(probe, args, hosts):
    pos = _positional(args, ("-w",))
    host = pos[0] if pos else ""
    port = int(pos[1]) if len(pos) > 1 and pos[1].isdigit() else 0
    ip = _resolve(host, hosts)
    if not ip:
        yield f"nc: getaddrinfo for host \"{host}\" port {port}: Name or service not known\n", 0
    elif _scenario(host)["dead"] or port not in OPEN_PORTS:
        yield f"nc: connect to {host} port {port} (tcp) failed: Connection timed out\n", 1.0
    else:
        yield f"Connection to {host} {port} port [tcp/*] succeeded!\n", 0


def tool_echo(probe, args, hosts):
    yield " ".join(args) + "\n", 0


def tool_hostname(probe, args, hosts):
    yield probe_hostname(probe) + "\n", 0


def tool_date(probe, args, hosts):
    yield datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y") + "\n", 0


def tool_uptime(probe, args, hosts):
    yield f" {datetime.utcnow():%H:%M:%S} up {1 + _h(probe) % 90} days,  1 user,  load average: 0.08, 0.05, 0.01\n", 0


def tool_whoami(probe, args, hosts):
    yield "root\n", 0


def tool_cat(probe, args, hosts):
    if args and args[0] == "/etc/hosts":
        yield "127.0.0.1 localhost\n" + "".join(f"{ip} {h}\n" for h, ip in hosts.items()), 0
    else:
        yield f"cat: {args[0] if args else ''}: Permission denied\n", 0


def tool_docker(probe, args, hosts):
    rest = [a for a in args if a not in ("run", "--rm")]
    if rest and rest[0] == "hctest01":
        yield from tool_httping(probe, rest[1:], hosts)
    else:
        yield "Unable to find image locally\n", 0


TOOLS = {"ping": tool_ping, "paping": tool_paping, "mtr": tool_mtr, "traceroute": tool_traceroute,
         "tcptraceroute": tool_traceroute, "dig": tool_dig, "nslookup": tool_nslookup, "host": tool_nslookup,
         "curl": tool_curl, "nc": tool_nc, "telnet": tool_nc, "echo": tool_echo, "hostname": tool_hostname,
         "date": tool_date, "uptime": tool_uptime, "whoami": tool_whoami, "cat": tool_cat, "docker": tool_docker}


# ---------------------------------------------------------------- command interpreter
_REDIR = re.compile(r"^(.*?)\s*(>>|>)\s*(\S+)(\s+2>&1)?\s*$", re.S)


def _probe_dir(probe, create=True):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]*", probe or "") or ".." in probe:
        raise SimConnectionError("invalid probe name")
    d = os.path.join(SIM_DIR, probe)
    if create:
        os.makedirs(d, exist_ok=True)
    return d


def _read_hosts(probe):
    hosts = {}
    p = os.path.join(_probe_dir(probe), "etc_hosts")
    if os.path.exists(p):
        for ln in open(p).read().splitlines():
            parts = ln.split()
            if len(parts) >= 2 and parts[0] != "127.0.0.1":
                for name in parts[1:]:
                    hosts[name] = parts[0]
    return hosts


def _unquote(seg):
    try:
        return shlex.split(seg)
    except ValueError:
        return seg.split()


def _split_script(script):
    parts, cur, q = [], "", None
    for ch in script:
        if q:
            cur += ch
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
            cur += ch
        elif ch == ";":
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _web_path(probe, name, create=True):
    name = os.path.basename(name)
    return os.path.join(_probe_dir(probe, create), name)


def _plan(probe, command):
    """Turn one shell command string into [(tool, args, target_file or None, append)]. Nothing is executed."""
    cmd = command.strip()
    cmd = re.sub(r"\s*&\s*$", "", cmd)
    cmd = re.sub(r"\s*>\s*/dev/null\s+2>&1\s*$", "", cmd)
    cmd = re.sub(r"^nohup\s+", "", cmd)
    m = re.match(r"^sh -c '(.*)'$", cmd, re.S)
    segments = _split_script(m.group(1)) if m else _split_script(cmd)
    plan = []
    for seg in segments:
        target, append = None, True
        r = _REDIR.match(seg)
        if r:
            seg, op, dest = r.group(1), r.group(2), r.group(3)
            if dest.startswith(WEB_ROOT):
                target, append = dest[len(WEB_ROOT):], op == ">>"
            elif dest == "/etc/hosts":
                target = "/etc/hosts"
                append = op == ">>"
            else:
                target = "/dev/null"
        words = _unquote(seg.replace("$HOSTNAME", probe_hostname(probe)))
        words = [w for w in words if w != "nohup"]
        plan.append((words, target, append))
    return plan


class _Stream:
    def __init__(self, text=""):
        self._t = text
        self.channel = self

    def read(self, *a):
        return self._t.encode()

    def readlines(self):
        return self._t.splitlines(True)

    def recv_exit_status(self):
        return 0


class AutoAddPolicy:
    pass


class SSHClient:
    """Look-alike of paramiko.SSHClient. Commands are interpreted, never executed."""

    def __init__(self):
        self.host = None
        self._last = None

    def set_missing_host_key_policy(self, policy):
        pass

    def connect(self, hostname, port=22, username=None, password=None, timeout=None, **kw):
        if not probe_is_up(hostname):
            raise TimeoutError(f"timed out connecting to {hostname}:{port}")
        self.host = hostname
        time.sleep(0.05)

    def exec_command(self, command, **kw):
        probe = self.host
        plan = _plan(probe, command)
        deferred = []
        for words, target, append in plan:
            if target == "/etc/hosts":
                p = os.path.join(_probe_dir(probe), "etc_hosts")
                line = " ".join(words[1:]) + "\n" if words and words[0] == "echo" else ""
                with open(p, "a" if append else "w") as f:
                    f.write(line)
            else:
                deferred.append((words, target, append))
        snapshot = _read_hosts(probe)
        prev = self._last
        t = threading.Thread(target=_run_plan, args=(probe, deferred, snapshot, prev), daemon=True)
        self._last = t
        t.start()
        return _Stream(), _Stream(), _Stream()

    def close(self):
        pass


def _run_plan(probe, plan, hosts, prev):
    if prev is not None:
        prev.join()
    for words, target, append in plan:
        if not words:
            continue
        tool = TOOLS.get(words[0])
        fh = None
        if target and target != "/dev/null":
            path = _web_path(probe, target)
            fh = open(path, "a" if append else "w")
        try:
            if tool is None:
                out = [(f"sh: 1: {words[0]}: not found\n", 0)]
            else:
                out = tool(probe, words[1:], hosts)
            try:
                for text, delay in out:
                    if fh:
                        fh.write(text)
                        fh.flush()
                    if delay:
                        time.sleep(delay)
            except (ValueError, ZeroDivisionError) as e:
                if fh:
                    fh.write(f"{words[0]}: invalid arguments ({e})\n")
        finally:
            if fh:
                fh.close()


# ---------------------------------------------------------------- the probe's "Apache"
class SimConnectionError(OSError):
    pass


class SimResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise SimConnectionError(f"{self.status_code} Client Error")


def fetch_result(probe, filename):
    """Replacement for requests.get(f'http://{probe}:8787/{filename}')."""
    if not probe_is_up(probe):
        raise SimConnectionError(f"Connection to {probe}:8787 timed out")
    if filename == "myip.txt":
        pub = probe_public_ip(probe)
        return SimResponse(200, f"SIM_{probe_hostname(probe)}_{pub},XX,simulated probe,{datetime.utcnow():%a_%Y-%m-%d_%H-%M-%S}\n")
    path = _web_path(probe, filename, create=False)
    if not os.path.exists(path):
        return SimResponse(404, "404 Not Found")
    with open(path) as f:
        return SimResponse(200, f.read())


def ltm_config_text(url):
    """Simulated LTM backup file: the Alpha datacenter file exists, the Bravo one does not (404)."""
    if "/Alpha_" not in url:
        return None
    return f"ltm pool demo_pool {{\n    members {{\n        {F5_DEMO_MEMBER}:80 {{ address {F5_DEMO_MEMBER} }}\n    }}\n}}\n"
