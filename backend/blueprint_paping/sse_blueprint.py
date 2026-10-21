import re
from flask import Blueprint, Response, request
import time
import random
import requests
from datetime import datetime
import sys
import os
import json
import queue
import concurrent.futures
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import probe_sim, probe_http
from utils.tcp_check import is_port_open
from utils import otel_span

sse_blueprint = Blueprint("sse_blueprint", __name__)


def format_paping_output(text):
    """Format the raw paping output to be cleaner"""
    import re
    # Remove paping header/copyright info
    result = text.replace("paping", "").replace("v1.5.5", "").replace(
        "Copyright ", ""
    ).replace("(c)", "").replace("2011", "").replace(
        "Mike ", ""
    ).replace("Lovell", "").replace(
        "Connected to", ""
    ).replace("protocol=TCP", "").replace(
        "time", "latency"
    ).replace("Connecting to", "").replace(
        "TCP", "Port"
    ).replace("Connection statistics", "").replace(
        "Approximate connection latencys", ""
    ).replace("Minimum", "Min").replace(
        "Maximum", "Max"
    ).replace("Average", "Avg").replace(
        "latencyd", "time"
    ).replace("port=", "").replace(
        "Attempted=", "Tested="
    ).replace("Connnected=", "Success=").replace(
        "    ", " "
    ).replace("?", "").replace("\n\n\n", "\n").replace(
        "\n\t", "\n"
    ).replace("= ", "=").replace(" =", "=").replace(
        "Attempted ", "Tested "
    ).replace("Connected ", "Success ").replace(
        "  ", " "
    )
    # Remove any remaining backspace characters
    result = result.replace("\b", "")
    # Clean up multiple spaces and newlines
    result = re.sub(r' +', ' ', result)
    result = re.sub(r'\n\s*\n', '\n', result)
    return result.strip()


def is_complete(result):
    """Check if the result indicates completion"""
    if not result:
        return False
    return (
        "---TCPING_COMPLETE---" in result or
        "---MTR_COMPLETE---" in result or
        "---DIG_COMPLETE---" in result or
        "Summary:" in result or
        "Failed=" in result or
        result.lstrip().lower().startswith("error")
    )


_PROBE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.:-]*")
_TARGET_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,252}")


def parse_batch_payload(payload, with_count):
    """Return (target, port, count, probes) or raise ValueError with a message."""
    target = payload.get('target')
    if not isinstance(target, str) or not _TARGET_RE.fullmatch(target):
        raise ValueError('target must be a host name or IP')
    try:
        port = int(payload.get('port', 443))
        count = int(payload.get('count', 20))
    except (TypeError, ValueError):
        raise ValueError('port and count must be integers')
    if not 1 <= port <= 65535:
        raise ValueError('port must be 1 to 65535')
    if with_count and not 1 <= count <= 100:
        raise ValueError('count must be 1 to 100')
    probes = payload.get('probes')
    if (not isinstance(probes, list) or not 1 <= len(probes) <= 20
            or not all(isinstance(p, str) and _PROBE_RE.fullmatch(p) for p in probes)):
        raise ValueError('probes must be a list of 1 to 20 probe IPs')
    return target, port, count, list(dict.fromkeys(probes))



@sse_blueprint.route('/sse/tcping/<target>/<port>/<count>/<probe_ip>')
def sse_tcping(target, port, count, probe_ip):
    """SSE endpoint for TCPing - streams results in real-time"""

    def generate():
        try:
            # Local probe - execute via SSH
            ssh_port = 52770

            if not is_port_open(probe_ip, ssh_port):
                yield f"data: error: Port {ssh_port} on {probe_ip} is not reachable (TCPing failed). SSH connection aborted.\n\n"
                return

            dt = datetime.now()
            time_in_microsecond = dt.microsecond
            filename = f"{time_in_microsecond}_{target}_ping_result_{probe_ip}"

            ssh = probe_sim.SSHClient()
            ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
            ssh.connect(probe_ip, ssh_port, "root", "sim", timeout=5)

            command = (
                f"nohup sh -c 'echo $HOSTNAME > /var/www/html/{filename}; "
                f"ping -c 1 {target} -W 1 >> /var/www/html/{filename}; "
                f"paping -c {count} {target} -p {port} --nocolor >> /var/www/html/{filename}; "
                f"echo ---TCPING_COMPLETE--- >> /var/www/html/{filename}' "
                "> /dev/null 2>&1 &"
            )
            ssh.exec_command(command)
            ssh.close()

            # Poll for results and stream them
            result_url = f"http://{probe_ip}:8787/{filename}"
            last_result = ""

            for attempt in range(20):
                time.sleep(1.0 if attempt < 3 else 1.5)

                try:
                    response = probe_http.fetch(result_url, timeout=5)
                    if response.status_code == 200:
                        result = format_paping_output(response.text)

                        # Only send if result changed
                        if result != last_result:
                            last_result = result
                            # Escape newlines for SSE
                            escaped = result.replace('\n', '\\n')
                            yield f"data: {escaped}\n\n"

                        if is_complete(result):
                            break
                except requests.RequestException:
                    pass

        except Exception as e:
            yield f"data: error: {str(e)}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'X-Accel-Buffering': 'no'
        }
    )


@sse_blueprint.route('/sse/mtr/<target>/<port>/<probe_ip>')
def sse_mtr(target, port, probe_ip):
    """SSE endpoint for MTR/TCP Trace - streams results in real-time"""

    def generate():
        try:
            # Local probe - execute via SSH
            ssh_port = 52770

            if not is_port_open(probe_ip, ssh_port):
                yield f"data: error: Port {ssh_port} on {probe_ip} is not reachable. SSH connection aborted.\n\n"
                return

            dt = datetime.now()
            time_in_microsecond = dt.microsecond
            filename = f"{time_in_microsecond}_{target}_mtr_result_{probe_ip}"

            ssh = probe_sim.SSHClient()
            ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
            ssh.connect(probe_ip, ssh_port, "root", "sim", timeout=5)

            # Use mtr -T (TCP mode) instead of tcptraceroute for better statistics
            # -T: TCP mode, -P: port, -n: no DNS, -c: count, -r: report mode
            command = (
                f"nohup sh -c 'echo $HOSTNAME > /var/www/html/{filename}; "
                f"mtr -T -P {port} -n -c 3 -r {target} >> /var/www/html/{filename}; "
                f"echo ---MTR_COMPLETE--- >> /var/www/html/{filename}' "
                "> /dev/null 2>&1 &"
            )
            ssh.exec_command(command)
            ssh.close()

            # Poll for results and stream them
            result_url = f"http://{probe_ip}:8787/{filename}"
            last_result = ""

            for attempt in range(40):
                time.sleep(2)

                try:
                    response = probe_http.fetch(result_url, timeout=5)
                    if response.status_code == 200:
                        result = response.text

                        if result != last_result:
                            last_result = result
                            escaped = result.replace('\n', '\\n')
                            yield f"data: {escaped}\n\n"

                        if "---MTR_COMPLETE---" in response.text:
                            break
                except requests.RequestException:
                    pass

        except Exception as e:
            yield f"data: error: {str(e)}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'X-Accel-Buffering': 'no'
        }
    )


@sse_blueprint.route('/sse/dig/<target>/<probe_ip>')
def sse_dig(target, probe_ip):
    """SSE endpoint for DIG - streams results in real-time"""

    def generate():
        try:
            # Local probe - execute via SSH
            ssh_port = 52770

            if not is_port_open(probe_ip, ssh_port):
                yield f"data: error: Port {ssh_port} on {probe_ip} is not reachable. SSH connection aborted.\n\n"
                return

            dt = datetime.now()
            time_in_microsecond = dt.microsecond
            filename = f"{time_in_microsecond}_{target}_dig_result_{probe_ip}"

            ssh = probe_sim.SSHClient()
            ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
            ssh.connect(probe_ip, ssh_port, "root", "sim", timeout=5)

            command = (
                f"nohup sh -c 'echo $HOSTNAME > /var/www/html/{filename}; "
                f"dig {target} >> /var/www/html/{filename}; "
                f"echo ---DIG_COMPLETE--- >> /var/www/html/{filename}' "
                "> /dev/null 2>&1 &"
            )
            ssh.exec_command(command)
            ssh.close()

            # Poll for results
            result_url = f"http://{probe_ip}:8787/{filename}"

            for attempt in range(10):
                time.sleep(1)

                try:
                    response = probe_http.fetch(result_url, timeout=5)
                    if response.status_code == 200 and len(response.text) > 50:
                        escaped = response.text.replace('\n', '\\n')
                        yield f"data: {escaped}\n\n"
                        break
                except requests.RequestException:
                    pass

        except Exception as e:
            yield f"data: error: {str(e)}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'X-Accel-Buffering': 'no'
        }
    )


# ============================================
# BATCH SSE ENDPOINTS - Run all probes simultaneously
# ============================================

def run_single_tcping(target, port, count, probe_ip, result_queue):
    """Execute tcping for a single probe and put results in queue"""
    try:
        # Local probe
        ssh_port = 52770
        if not is_port_open(probe_ip, ssh_port):
            result_queue.put({
                "probe_ip": probe_ip,
                "data": f"error: Port {ssh_port} on {probe_ip} is not reachable",
                "complete": True
            })
            return

        dt = datetime.now()
        filename = f"{dt.microsecond}_{target}_ping_result_{probe_ip}"

        ssh = probe_sim.SSHClient()
        ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
        ssh.connect(probe_ip, ssh_port, "root", "sim", timeout=5)

        command = (
            f"nohup sh -c 'echo $HOSTNAME > /var/www/html/{filename}; "
            f"ping -c 1 {target} -W 1 >> /var/www/html/{filename}; "
            f"paping -c {count} {target} -p {port} --nocolor >> /var/www/html/{filename}; "
            f"echo ---TCPING_COMPLETE--- >> /var/www/html/{filename}' "
            "> /dev/null 2>&1 &"
        )
        ssh.exec_command(command)
        ssh.close()

        result_url = f"http://{probe_ip}:8787/{filename}"
        last_result = ""

        for attempt in range(20):
            time.sleep(1.0 if attempt < 3 else 1.5)
            try:
                response = probe_http.fetch(result_url, timeout=5)
                if response.status_code == 200:
                    result = format_paping_output(response.text)
                    if result != last_result:
                        last_result = result
                        result_queue.put({
                            "probe_ip": probe_ip,
                            "data": result,
                            "complete": is_complete(result)
                        })
                    if is_complete(result):
                        return
            except requests.RequestException:
                pass

        # Timeout - no complete result after all attempts
        if not last_result:
            result_queue.put({
                "probe_ip": probe_ip,
                "data": "error: Probe timed out - no response received",
                "complete": True
            })
        elif not is_complete(last_result):
            result_queue.put({
                "probe_ip": probe_ip,
                "data": last_result + "\n\nerror: TCPing did not complete in time",
                "complete": True
            })

    except Exception as e:
        result_queue.put({
            "probe_ip": probe_ip,
            "data": f"error: {str(e)}",
            "complete": True
        })


def run_single_mtr(target, port, probe_ip, result_queue):
    """Execute MTR for a single probe and put results in queue"""
    try:
        # Local probe
        ssh_port = 52770
        if not is_port_open(probe_ip, ssh_port):
            result_queue.put({
                "probe_ip": probe_ip,
                "data": f"error: Port {ssh_port} on {probe_ip} is not reachable",
                "complete": True
            })
            return

        dt = datetime.now()
        filename = f"{dt.microsecond}_{target}_mtr_result_{probe_ip}"

        ssh = probe_sim.SSHClient()
        ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
        ssh.connect(probe_ip, ssh_port, "root", "sim", timeout=5)

        # Use mtr -T (TCP mode) instead of tcptraceroute for better statistics
        # -T: TCP mode, -P: port, -n: no DNS, -c: count, -r: report mode
        command = (
            f"nohup sh -c 'echo $HOSTNAME > /var/www/html/{filename}; "
            f"mtr -T -P {port} -n -c 3 -r {target} >> /var/www/html/{filename}; "
            f"echo ---MTR_COMPLETE--- >> /var/www/html/{filename}' "
            "> /dev/null 2>&1 &"
        )
        ssh.exec_command(command)
        ssh.close()

        result_url = f"http://{probe_ip}:8787/{filename}"
        last_result = ""

        for attempt in range(40):
            time.sleep(2)
            try:
                response = probe_http.fetch(result_url, timeout=5)
                if response.status_code == 200:
                    result = response.text
                    if result != last_result:
                        last_result = result
                        result_queue.put({
                            "probe_ip": probe_ip,
                            "data": result,
                            "complete": "---MTR_COMPLETE---" in response.text
                        })
                    if "---MTR_COMPLETE---" in response.text:
                        return
            except requests.RequestException:
                pass

        # Timeout - no complete result after all attempts
        if not last_result:
            result_queue.put({
                "probe_ip": probe_ip,
                "data": "error: Probe timed out - no response received",
                "complete": True
            })
        elif "---MTR_COMPLETE---" not in last_result:
            result_queue.put({
                "probe_ip": probe_ip,
                "data": last_result + "\n\nerror: tcptraceroute did not complete in time",
                "complete": True
            })

    except Exception as e:
        result_queue.put({
            "probe_ip": probe_ip,
            "data": f"error: {str(e)}",
            "complete": True
        })


@sse_blueprint.route('/sse/batch/tcping', methods=['POST', 'OPTIONS'])
def sse_batch_tcping():
    """
    Batch SSE endpoint for TCPing - runs all probes simultaneously.

    POST body (JSON):
    {
        "target": "example.com",
        "port": 443,
        "count": 20,
        "probes": ["192.0.2.11", "192.0.2.12", ...]
    }

    SSE output (JSON per message):
    data: {"probe_ip": "192.0.2.12", "data": "...", "complete": false}
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response('', headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

    payload = request.get_json(silent=True) or {}
    try:
        target, port, count, probes = parse_batch_payload(payload, True)
    except ValueError as e:
        return Response(str(e), status=400)

    ctx = otel_span.capture()

    def generate():
        with otel_span.batch("batch tcping", ctx, target=target, port=port, probes=len(probes)) as bctx:
            yield from _stream_tcping(bctx)

    def _stream_tcping(ctx):
        result_queue = queue.Queue()
        completed_probes = set()

        # Start all probes in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(probes)) as executor:  # probes deduplicated above
            futures = [
                executor.submit(otel_span.run_probe, ctx, "probe tcping", run_single_tcping, probe_ip, target, port, count, probe_ip, result_queue)
                for probe_ip in probes
            ]

            # Stream results as they arrive
            while len(completed_probes) < len(probes):
                try:
                    result = result_queue.get(timeout=1)
                    yield f"data: {json.dumps(result)}\n\n"
                    if result.get('complete'):
                        completed_probes.add(result['probe_ip'])
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'heartbeat': True})}\n\n"

            # Wait for all threads to finish
            concurrent.futures.wait(futures)

        # Send final completion message
        yield f"data: {json.dumps({'all_complete': True})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'X-Accel-Buffering': 'no'
        }
    )


@sse_blueprint.route('/sse/batch/mtr', methods=['POST', 'OPTIONS'])
def sse_batch_mtr():
    """
    Batch SSE endpoint for MTR - runs all probes simultaneously.

    POST body (JSON):
    {
        "target": "example.com",
        "port": 443,
        "probes": ["192.0.2.11", "192.0.2.12", ...]
    }

    SSE output (JSON per message):
    data: {"probe_ip": "192.0.2.12", "data": "...", "complete": false}
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return Response('', headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

    payload = request.get_json(silent=True) or {}
    try:
        target, port, count, probes = parse_batch_payload(payload, False)
    except ValueError as e:
        return Response(str(e), status=400)

    ctx = otel_span.capture()

    def generate():
        with otel_span.batch("batch mtr", ctx, target=target, port=port, probes=len(probes)) as bctx:
            yield from _stream_mtr(bctx)

    def _stream_mtr(ctx):
        result_queue = queue.Queue()
        completed_probes = set()

        # Start all probes in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(probes)) as executor:  # probes deduplicated above
            futures = [
                executor.submit(otel_span.run_probe, ctx, "probe mtr", run_single_mtr, probe_ip, target, port, probe_ip, result_queue)
                for probe_ip in probes
            ]

            # Stream results as they arrive
            while len(completed_probes) < len(probes):
                try:
                    result = result_queue.get(timeout=2)
                    yield f"data: {json.dumps(result)}\n\n"
                    if result.get('complete'):
                        completed_probes.add(result['probe_ip'])
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'heartbeat': True})}\n\n"

            # Wait for all threads to finish
            concurrent.futures.wait(futures)

        # Send final completion message
        yield f"data: {json.dumps({'all_complete': True})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'X-Accel-Buffering': 'no'
        }
    )