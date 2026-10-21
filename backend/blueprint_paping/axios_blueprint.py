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

axios_blueprint = Blueprint("axios_blueprint", __name__)
from model import db, b11_huck_ge_probes,c10_for_paping_probes
import sys
import os
# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import probe_sim, probe_http


# #######################################################################
@axios_blueprint.route('/axios_paping_server_ip/<which_isp>')
@axios_blueprint.route('/axios_paping_server_ip')
@axios_blueprint.route('/axios_paping_server_ip/')
def axios_paping_server_ip_ct(which_isp="CT"):
    # 1. Get local probes (always shown as primary)
    local_probes = []
    try:
        list_whole_db_b11_huck_ge_probes = b11_huck_ge_probes.query.filter(b11_huck_ge_probes.isp_expected == which_isp).all()
        local_probes = [data.serialize for data in list_whole_db_b11_huck_ge_probes]
    except Exception as e:
        print(f"Error fetching local probes (DB might be down or schema mismatch): {e}")
    
    return jsonify(local_probes)


#######################################################################
# Route that frontend_webtcping expects (mirrors the route above)
@axios_blueprint.route('/axios_show_which_host_isp_for_webpaping/<which_isp>')
@axios_blueprint.route('/axios_show_which_host_isp_for_webpaping')
@axios_blueprint.route('/axios_show_which_host_isp_for_webpaping/')
def axios_show_which_host_isp_for_webpaping(which_isp="CT"):
    return axios_paping_server_ip_ct(which_isp)


#######################################################################
# Route for getting specific probe by city
@axios_blueprint.route('/axios_show_which_probe_for_webpaping/<which_city>')
def axios_show_which_probe_for_webpaping(which_city="Beijing"):
    try:
        # ge_city is the actual model attribute (maps to 'city' column in DB)
        probe = b11_huck_ge_probes.query.filter(b11_huck_ge_probes.ge_city == which_city).first()
        if probe:
            return jsonify(probe.serialize)
        return jsonify({"error": f"probe not found for city: {which_city}"})
    except Exception as e:
        print(f"Error fetching probe: {e}")
        return jsonify({"error": str(e)})


#######################################################################
#######################################################################
# Route for updating a probe's public IP by fetching from its myip.txt endpoint
@axios_blueprint.route('/update_probe_public_ip/<int:probe_id>', methods=['POST'])
def update_probe_public_ip(probe_id):
    """
    Fetch the public IP from a probe's myip.txt endpoint and update the database.

    Args:
        probe_id: The probe's database ID

    Returns:
        JSON with success status and the new public IP, or error message
    """
    try:
        # Find the probe by ID
        probe = b11_huck_ge_probes.query.get(probe_id)
        if not probe:
            return jsonify({"error": "Probe not found", "success": False}), 404

        # Skip if no private IP
        if not probe.ge_server_private_ip:
            return jsonify({"error": "No private IP configured for this probe", "success": False}), 400

        # Fetch the public IP from the probe's myip.txt endpoint
        myip_url = f"http://{probe.ge_server_private_ip}:8787/myip.txt"
        response = probe_http.fetch(myip_url, timeout=10)

        if response.status_code != 200:
            return jsonify({"error": f"Failed to fetch from probe: HTTP {response.status_code}", "success": False}), 502

        # Get the public IP from the response
        # Response format: "ISP_City_IP,Country,ISP_Full_Name,Timestamp"
        # e.g., "3BB_Bankok001_171.7.18.90,TH,triple t broadband public company limited,Alpha_2026-02-05_09-00-02"
        raw_response = response.text.strip()

        # Extract IP using regex pattern
        ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        ip_match = re.search(ip_pattern, raw_response)

        if not ip_match:
            return jsonify({"error": f"Could not find IP in response: {raw_response}", "success": False}), 502

        new_public_ip = ip_match.group(1)

        # Update the database
        probe.public_ip = new_public_ip
        db.session.commit()

        return jsonify({
            "success": True,
            "public_ip": new_public_ip,
            "probe_id": probe_id,
            "hostname": probe.hostname,
            "city": probe.ge_city
        })

    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout connecting to probe", "success": False}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Network error: {str(e)}", "success": False}), 502
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}", "success": False}), 500


#######################################################################
@axios_blueprint.route('/another_version_axios_paping_server_ip/<which_isp>')
@axios_blueprint.route('/another_version_axios_paping_server_ip')
@axios_blueprint.route('/another_version_axios_paping_server_ip/')
def another_version_axios_paping_server_ip_ct(which_isp="CT"):
    list_whole_db_c10_for_paping_probes = c10_for_paping_probes.query.filter(
        c10_for_paping_probes.which_isp == which_isp).all()
    list_whole_db_c10_for_paping_probes = [
        data.serialize for data in list_whole_db_c10_for_paping_probes
    ]
    return jsonify(list_whole_db_c10_for_paping_probes)
