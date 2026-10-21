from flask import Flask, render_template, redirect, url_for, jsonify, session, json, Blueprint,request
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
from utils import probe_sim
from utils.tcp_check import is_port_open
customized_command_blueprint = Blueprint("customized_command_blueprint", __name__)


#######################################################################
@customized_command_blueprint.route("/e01_action_customized_command", methods=["GET"])
def handle_custom_command():
    cmd = request.args.get("cmd")
    ip = request.args.get("ip")

    if not cmd or not ip:
        return "Missing cmd or ip", 400

    try:
        result_filename = action_paping_to_ge_probes(cmd, ip)
        return result_filename
    except Exception as e:
        return f"Server error: {str(e)}", 500


#######################################################################
# @customized_command_blueprint.route('/e01_action_customized_command/<customized_command>/<which_GE_server>')
# def action_paping_to_ge_probes(customized_command,which_GE_server):
#     # ping_result=dt.microsecond
#     # # this would create a random filename on the remote server
#     ######### inserting time into the session #########
#     # session.pop('user', None) #clear the session first, so that
#     try:
#         dt = datetime.now()
#         time_in_microsecond = dt.microsecond
#         session['user'] = str(time_in_microsecond)

#         #####################################################
#         # return session['user']
#         port = 52770
#         ssh = probe_sim.SSHClient()
#         ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
#         ssh.connect(which_GE_server, port, "root", "sim")
#         filename_for_paping_located_in_GE_apache = session['user'] + "_" + "customized_command" + "_" + which_GE_server
#         print(f"filename_for_paping_located_in_GE_apache={filename_for_paping_located_in_GE_apache}")
#         stdin, stdout, stderr = ssh.exec_command("echo $HOSTNAME > /var/www/html/%s" %(filename_for_paping_located_in_GE_apache))
#         stdin, stdout, stderr = ssh.exec_command(f"{customized_command} >> /var/www/html/{filename_for_paping_located_in_GE_apache}")
#         print(f"stdout={stdout} / stderr={stderr} / customized_command={customized_command}")

#         ssh.close()

#         return filename_for_paping_located_in_GE_apache
#     except Exception as error:
#         return f"Exception={Exception} / error = cannot connect to probe"


#######################################################################
def action_paping_to_ge_probes(customized_command, which_GE_server):
    try:
        dt = datetime.now()
        time_in_microsecond = dt.microsecond
        session['user'] = str(time_in_microsecond)

        port = 52770
        
        # TCPing pre-check
        if not is_port_open(which_GE_server, port):
             return f"error: Port {port} on {which_GE_server} is not reachable (TCPing failed). SSH connection aborted."

        ssh = probe_sim.SSHClient()
        ssh.set_missing_host_key_policy(probe_sim.AutoAddPolicy())
        ssh.connect(which_GE_server, port, "root", "sim", timeout=5)

        filename = f"{session['user']}_customized_command_{which_GE_server}"
        print(f"filename_for_paping_located_in_GE_apache={filename}")

        # Try to extract target from command for ping pre-check
        target_for_ping = None
        parts = customized_command.split()
        if len(parts) >= 2:
            # Common tools where target is usually the last argument or after flags
            # This is a best-effort heuristic
            if parts[0] in ["ping", "dig", "nslookup", "curl", "wget", "mtr", "paping", "nc", "telnet"]:
                # Take the last argument that doesn't look like a flag
                for part in reversed(parts):
                    if not part.startswith("-"):
                        target_for_ping = part
                        break

        # Construct chained command with nohup
        command_parts = [f"echo $HOSTNAME > /var/www/html/{filename}"]
        
        if target_for_ping:
             # Clean up target (remove protocol, port, etc if simple)
             if "://" in target_for_ping:
                 target_for_ping = target_for_ping.split("://")[1].split("/")[0]
             if ":" in target_for_ping:
                 target_for_ping = target_for_ping.split(":")[0]
                 
             command_parts.append(f"ping -c 1 {target_for_ping} -W 1 >> /var/www/html/{filename}")
             
        command_parts.append(f"{customized_command} >> /var/www/html/{filename}")
        
        full_command = "nohup sh -c '" + "; ".join(command_parts) + "' > /dev/null 2>&1 &"
        
        ssh.exec_command(full_command)
        print(f"customized_command={customized_command}")

        ssh.close()

        return filename

    except Exception as error:
        print(f"[ERROR] {error}")
        return f"Exception={type(error).__name__} / error = cannot connect to probe"


