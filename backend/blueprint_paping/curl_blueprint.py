from flask import Flask, render_template, redirect, url_for, jsonify, session, json, Blueprint, request
import os
import requests
import time
import re
# from file_func_current_connection import func_prtg_current_outgoing_traffic,func_peakbw,func_prtg_current_connection
import datetime

current_Time = datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
# starting_one_hour_ago=(datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
# from forms import User_enter_IP_and_show_result
from datetime import datetime
import sys
import os
# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import probe_sim, probe_http
from utils.tcp_check import is_port_open
from utils.url_helper import parse_target_url, sanitize_filename

curl_blueprint = Blueprint("curl_blueprint", __name__)

#******************this route is for doing mtr***************************


@curl_blueprint.route('/d01_do_curl_to_ge_probes', methods=["GET", "POST"])
@curl_blueprint.route('/d01_do_curl_to_ge_probes/', methods=["GET", "POST"])
def d01_do_curl_to_ge_probes():
    # ping_result=dt.microsecond
    # # this would create a random filename on the remote server
    ######### inserting time into the session #########
    # session.pop('user', None) #clear the session first, so that
    if request.method == "POST":
        request_data = request.data
        dict_request_data = json.loads(request_data)

        # Validate required fields
        if "probe_ip" not in dict_request_data or not dict_request_data["probe_ip"]:
            return "error: probe_ip is required", 400

        target_ip_for_wget = dict_request_data.get("getting_the_ip_or_url_from_vuex", "")
        which_GE_server = dict_request_data["probe_ip"]
        ip_for_hostfile = dict_request_data.get("ip_for_hostfile_from_vuex", "")
        url_for_hostfile = dict_request_data.get("url_for_hostfile_from_vuex", "")
        http1_1_or_http2 = dict_request_data.get("getting_the_port_from_vuex", "HTTP1.1")
        getting_the_tls_version_from_vuex = dict_request_data.get("getting_the_tls_version_from_vuex", "Auto")
        
        dt = datetime.now()
        time_in_microsecond = dt.microsecond
        session['user'] = str(time_in_microsecond)

        #####################################################
        # print(f"http1_1_or_http2={http1_1_or_http2}")
        # return session['user']
        port = 52770
        ssh = probe_sim.SSHClient()
        ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
        which_GE_server  #ZJ_IDC
        
        # TCPing pre-check
        if not is_port_open(which_GE_server, port):
             return f"error: Port {port} on {which_GE_server} is not reachable (TCPing failed). SSH connection aborted."

        ssh.connect(which_GE_server, port, "root", "sim", timeout=5)

        # Parse the target URL to extract hostname for ping command
        parsed_target = parse_target_url(target_ip_for_wget)
        target_hostname = parsed_target["hostname"]
        print(f"[DEBUG] target_ip_for_wget={target_ip_for_wget}, parsed hostname={target_hostname}")

        # Sanitize filename to handle URLs with paths like /service/api/status
        sanitized_target = sanitize_filename(target_ip_for_wget)
        filename_for_paping_located_in_GE_apache = session['user'] + "_" + sanitized_target + "_result_" + which_GE_server

        # flushing the hostfile
        stdin, stdout, stderr = ssh.exec_command("""echo "127.0.0.1 localhost" > /etc/hosts""")
        stdin, stdout, stderr = ssh.exec_command(f"""echo "{ip_for_hostfile} {url_for_hostfile}" >> /etc/hosts""")

        stdin, stdout, stderr = ssh.exec_command(
            "echo $HOSTNAME > /var/www/html/%s" %
            (filename_for_paping_located_in_GE_apache))

        stdin, stdout, stderr = ssh.exec_command(
            f"""echo 'ping 1 packet, to make sure that hostfile is working'>> /var/www/html/{filename_for_paping_located_in_GE_apache}"""
        )
        # Use hostname for ping command (not full URL with path)
        target_ip_for_nslookup = target_hostname
        stdin, stdout, stderr = ssh.exec_command(
            f"ping -c 1 {target_ip_for_nslookup} -W 1 >> /var/www/html/{filename_for_paping_located_in_GE_apache} 2>&1"
        )
        time.sleep(2)
        stdin, stdout, stderr = ssh.exec_command(
            f"""echo =============================================================>> /var/www/html/{filename_for_paping_located_in_GE_apache}"""
        )
        # Build TLS flag - "Auto" means no --tls-max restriction (let curl negotiate best version)
        tls_flag = "" if getting_the_tls_version_from_vuex == "Auto" else f"--tls-max {getting_the_tls_version_from_vuex}"

        if http1_1_or_http2 == "HTTP1.1":
            print(f"getting_the_tls_version_from_vuex={getting_the_tls_version_from_vuex}")
            stdin, stdout, stderr = ssh.exec_command(
                f"nohup curl -ILk {tls_flag} --http1.1 -m 10 {target_ip_for_wget} >> /var/www/html/{filename_for_paping_located_in_GE_apache} 2>&1 &"
            )
        elif http1_1_or_http2 == "HTTP2":
            stdin, stdout, stderr = ssh.exec_command(
                f"nohup curl -ILk {tls_flag} -m 10 --http2 {target_ip_for_wget} >> /var/www/html/{filename_for_paping_located_in_GE_apache} 2>&1 &"
            )
        stdin, stdout, stderr = ssh.exec_command("""echo "127.0.0.1 localhost" > /etc/hosts""")
        stdin, stdout, stderr = ssh.exec_command("""echo "127.0.0.1 $HOSTNAME" >> /etc/hosts""")
        

        ssh.close()

        return filename_for_paping_located_in_GE_apache
