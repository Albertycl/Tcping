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
from model import db, b11_huck_ge_probes
import sys
import os
# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import probe_sim, probe_http
from utils.tcp_check import is_port_open
from utils.url_helper import parse_target_url, sanitize_filename

paping_blueprint = Blueprint("paping_blueprint", __name__)


#######################################################################
@paping_blueprint.route(
    '/a01_action_paping_to_ge_probes/<target_ip_for_paping>/<target_port>/<repeat_how_many_times>/<which_GE_server>'
)
@paping_blueprint.route('/a01_action_paping_to_ge_probes/')
@paping_blueprint.route('/a01_action_paping_to_ge_probes')
def action_paping_to_ge_probes(target_ip_for_paping="203.0.113.10",
                               target_port="443",
                               repeat_how_many_times="20",
                               which_GE_server="192.0.2.12"):
    # ping_result=dt.microsecond
    # # this would create a random filename on the remote server
    ######### inserting time into the session #########
    # session.pop('user', None) #clear the session first, so that
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

        # Parse the target URL to extract hostname for paping command
        parsed_target = parse_target_url(target_ip_for_paping)
        target_hostname = parsed_target["hostname"]

        # Sanitize filename to handle URLs with paths like /service/api/status
        sanitized_target = sanitize_filename(target_ip_for_paping)
        filename_for_paping_located_in_GE_apache = session['user'] + "_" + sanitized_target + "_ping_result_" + which_GE_server

        # Construct chained command with nohup (use hostname, not full URL for paping)
        command = (
            f"nohup sh -c 'echo $HOSTNAME > /var/www/html/{filename_for_paping_located_in_GE_apache}; "
            f"ping -c 1 {target_hostname} -W 1 >> /var/www/html/{filename_for_paping_located_in_GE_apache}; "
            f"paping -c {repeat_how_many_times} {target_hostname} -p {target_port} --nocolor >> /var/www/html/{filename_for_paping_located_in_GE_apache}' "
            "> /dev/null 2>&1 &"
        )
        ssh.exec_command(command)
        ssh.close()

        return filename_for_paping_located_in_GE_apache
    except Exception as error:
        return f"Exception={error} / error = cannot connect to probe"



# class class_paping:
#     def __init__(self):
#         self.server_private_ip=None
#         self.isp=None
#         self.country=None
        
#     def method_get_probe_ip(self):
#         all_the_rows_for_the_probe_ip=b11_huck_ge_probes.query.all()
#         for each_row in all_the_rows_for_the_probe_ip:
#             print(f"each_row={each_row}")
        
        
# @paping_blueprint.route('/test_latency')
# @paping_blueprint.route('/test_latency/')
# def test_latency():
#     paping_obj=class_paping()
#     paping_obj.method_get_probe_ip()
#     return "1"