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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import probe_sim, probe_http

show_papaing_or_mtr_result_by_querying_apache_blueprint = Blueprint(
    "show_papaing_or_mtr_result_by_querying_apache_blueprint", __name__)


#######################################################################
@show_papaing_or_mtr_result_by_querying_apache_blueprint.route('/a02_opening_apache_on_golden_eye_server/<filename_on_GE>/<ip_for_which_GE_server>'
)
@show_papaing_or_mtr_result_by_querying_apache_blueprint.route('/a02_opening_apache_on_golden_eye_server')
@show_papaing_or_mtr_result_by_querying_apache_blueprint.route('/a02_opening_apache_on_golden_eye_server/')
def a02_opening_apache_on_golden_eye_server(filename_on_GE="262123_www.example.com_result_192.0.2.11",ip_for_which_GE_server="192.0.2.11"):
    # if "user" in session:
    # return "in route read session, your session is %s" %(session["user"])
    
    if filename_on_GE.endswith("_tcping"):
        filename_on_GE = filename_on_GE.replace("_tcping", "")

    from time import sleep
    attempts = 0
    max_attempts = 5
    while attempts < max_attempts:
        try:
            ping_result_url = f"http://{ip_for_which_GE_server}:8787/{filename_on_GE}"
            print(f"ping_result_url={ping_result_url}")
            response = probe_http.fetch(ping_result_url)
            response.raise_for_status()
            print("Request was successful")

            response_text = response.text.replace(
                "paping", "\b\b\b\b\b"
            ).replace("v1.5.5", "\b\b\b\b\b").replace(" -", "\b\b").replace(
                "Copyright ", "\b\b\b"
            ).replace("(c)", "\b\b\b\b\b").replace("2011", "\b\b\b\b").replace(
                "Mike ", "\b\b\b\b"
            ).replace(
                "Lovell", "\b\b\b\b"
            ).replace(
                ":", " "
            ).replace(
                "Connected to",
                "\b\b\b\b"
            ).replace(
                "protocol=TCP",
                ""
            ).replace(
                "time",
                "latency"
            ).replace(
                "Connecting to", ""
            ).replace("TCP", "Port").replace(
                "Connection statistics",
                ""
            ).replace("Approximate connection latencys", "").replace(
                "Minimum", "Min"
            ).replace(
                "Maximum", "Max"
            ).replace(
                "Average", "Avg"
            ).replace(
                "latencyd",
                "time"
            ).replace("port=", "").replace(
                "Attempted=",
                "A="
            ).replace(
                "Connnected=", "C="
            ).replace("Failed=", "F=").replace(
                "\n\b\b\b\b\b \b\b\b\b\b  \b\b\b\b\b\b\b\b \b\b\b\b \b\b\b\b\b\b\b\b\n",
                "").replace(
                    "    ", "").replace(
                        "?", "").replace("\n\n\n", "").replace(
                            "\n\t",
                            "").replace("= ", "=").replace(
                                " =", "=").replace(
                                    "Attempted ",
                                    "Tested "
                                ).replace(
                                    "Connected ",
                                    "Success "
                                ).replace(
                                    "Failed ",
                                    "Failed "
                                )
            
            return response_text
        except requests.RequestException as error:
            print(f"Attempt {attempts + 1} failed with error: {error}")
            attempts += 1
            if attempts < max_attempts:
                sleep(1) # Optional: Wait for a second before the next attempt
            else:
                print("All attempts failed. Exiting.")
                # You can add more error handling here if neede
    return f"cannot open this url = {ping_result_url}"
