from flask import Flask, render_template, redirect, url_for, jsonify, session, json, Blueprint
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

mtr_blueprint = Blueprint("mtr_blueprint", __name__)


#******************this route is for doing mtr***************************
@mtr_blueprint.route(
    '/b01_do_mtr_to_ge_probes/<target_ip_for_mtr>/<target_port>/<which_GE_server>'
)
@mtr_blueprint.route('/b01_do_mtr_to_ge_probes')
@mtr_blueprint.route('/b01_do_mtr_to_ge_probes/')
def b01_do_mtr_to_ge_probes(target_ip_for_mtr="203.0.113.10",target_port="443",which_GE_server="192.0.2.11"):
    # ping_result=dt.microsecond
    # # this would create a random filename on the remote server
    ######### inserting time into the session #########
    # session.pop('user', None) #clear the session first, so that
    # session.pop('user', None) #clear the session first, so that
    
    dt = datetime.now()
    time_in_microsecond = dt.microsecond
    session['user'] = str(time_in_microsecond)

    #####################################################
    # return session['user']
    port = 52770
    ssh = probe_sim.SSHClient()
    ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
    
    try:
        # port = 52770
        
        # TCPing pre-check
        if not is_port_open(which_GE_server, port):
             return f"error: Port {port} on {which_GE_server} is not reachable (TCPing failed). SSH connection aborted."

        ssh.connect(which_GE_server, port, "root", "sim", timeout=20)

        # Parse the target URL to extract hostname for mtr/ping commands
        parsed_target = parse_target_url(target_ip_for_mtr)
        target_hostname = parsed_target["hostname"]

        # Sanitize filename to handle URLs with paths like /service/api/status
        sanitized_target = sanitize_filename(target_ip_for_mtr)
        filename_for_paping_located_in_GE_apache = session['user'] + "_" + sanitized_target + "_result_" + which_GE_server

        # Construct chained command with nohup (use hostname, not full URL for mtr/ping)
        # Add ---MTR_COMPLETE--- marker at end so frontend knows when mtr finished
        command = (
            f"nohup sh -c 'hostname > /var/www/html/{filename_for_paping_located_in_GE_apache}; "
            f"echo $HOSTNAME > /var/www/html/{filename_for_paping_located_in_GE_apache}; "
            f"ping -c 1 {target_hostname} -W 1 >> /var/www/html/{filename_for_paping_located_in_GE_apache}; "
            f"mtr -c 4 -w -z -n {target_hostname} >> /var/www/html/{filename_for_paping_located_in_GE_apache} 2>&1; "
            f"echo \"---MTR_COMPLETE---\" >> /var/www/html/{filename_for_paping_located_in_GE_apache}' "
            "> /dev/null 2>&1 &"
        )
        ssh.exec_command(command)
        ssh.close()
        # print(
        #     f"filename_for_paping_located_in_GE_apache={filename_for_paping_located_in_GE_apache}"
        # )
        return filename_for_paping_located_in_GE_apache
    except Exception as e:
        print(f"SSH connection failed to {which_GE_server}: {e}")
        return f"error: {str(e)}"

    return filename_for_paping_located_in_GE_apache

