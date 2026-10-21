from flask import Flask, render_template, redirect, url_for, jsonify, session, json, Blueprint, request
import os
import requests
# import re
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

http_ping_blueprint = Blueprint("http_ping_blueprint", __name__)


#######################################################################
@http_ping_blueprint.route(
    '/e01_http_ping/<target_ip_for_paping>/<which_GE_server>/<http_or_https>')
@http_ping_blueprint.route('/e01_http_ping/')
@http_ping_blueprint.route('/e01_http_ping')
def e01_http_ping(target_ip_for_paping="203.0.113.10",
                  which_GE_server="192.0.2.12",
                  http_or_https="http"):
    # ping_result=dt.microsecond
    # # this would create a random filename on the remote server
    ######### inserting time into the session #########
    # session.pop('user', None) #clear the session first, so that
    http_or_https = http_or_https.lower()
    http_or_https = http_or_https.lower()
    
    try:
        dt = datetime.now()
        time_in_microsecond = dt.microsecond
        session['user'] = str(time_in_microsecond)

        #####################################################
        # return session['user']
        port = 52770
        
        # TCPing pre-check
        if not is_port_open(which_GE_server, port):
             return f"error: Port {port} on {which_GE_server} is not reachable (TCPing failed). SSH connection aborted."

        ssh = probe_sim.SSHClient()
        ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
        ssh.connect(which_GE_server, port, "root", "sim", timeout=5)

        # Parse the target URL to extract hostname for ping command
        parsed_target = parse_target_url(target_ip_for_paping)
        target_hostname = parsed_target["hostname"]

        # Sanitize filename to handle URLs with paths like /service/api/status
        sanitized_target = sanitize_filename(target_ip_for_paping)
        filename_for_paping_located_in_GE_apache = session['user'] + "_" + sanitized_target + "_ping_result_" + which_GE_server

        # Build the full URL for httping - if target already has scheme, use it as-is
        # Otherwise construct with the provided scheme
        if parsed_target["is_url"]:
            httping_url = target_ip_for_paping  # Already has scheme and path
        else:
            httping_url = f"{http_or_https}://{target_ip_for_paping}"

        # Construct chained command with nohup
        # Note: Using the docker command that was previously commented out, as it seems to be the intended 'main' command
        command = (
            f"nohup sh -c 'echo $HOSTNAME > /var/www/html/{filename_for_paping_located_in_GE_apache}; "
            f"ping -c 1 {target_hostname} -W 1 >> /var/www/html/{filename_for_paping_located_in_GE_apache}; "
            f"docker run --rm hctest01 -c 20 -Ggsb {httping_url} >> /var/www/html/{filename_for_paping_located_in_GE_apache} 2>&1' "
            "> /dev/null 2>&1 &"
        )
        ssh.exec_command(command)
        ssh.close()

        return filename_for_paping_located_in_GE_apache
    except Exception as error:
        return f"error = cannot connect to probe"


# #######################################################################
@http_ping_blueprint.route('/testing_httping/')
@http_ping_blueprint.route('/testing_httping')
def testing_httping():
    return "1"