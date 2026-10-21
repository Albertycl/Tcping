from flask import Flask, render_template, redirect, url_for, jsonify, session, json
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

from blueprint_paping.paping_blueprint import paping_blueprint
from blueprint_paping.mtr_blueprint import mtr_blueprint
from blueprint_paping.axios_blueprint import axios_blueprint
from blueprint_paping.show_papaing_or_mtr_result_by_querying_apache_blueprint import show_papaing_or_mtr_result_by_querying_apache_blueprint
from blueprint_paping.dig_blueprint import dig_blueprint
from blueprint_paping.curl_blueprint import curl_blueprint
from blueprint_paping.http_ping_blueprint import http_ping_blueprint
from blueprint_paping.customized_command_blueprint import customized_command_blueprint

#########Migrations#############
from flask import request
app = Flask(__name__)


@app.before_request
def reject_unsafe_arguments():
    for key, value in (request.view_args or {}).items():
        v = str(value)
        if "port" in key or "repeat" in key or key == "count":
            if not v.isdigit() or not (1 <= int(v) <= (65535 if "port" in key else 100)):
                return "invalid " + key, 400
        elif any(w in key for w in ("target", "server", "probe", "ip_for")) and re.search(r"[;|&$`<>\\'\"\s]", v):
            return "invalid " + key, 400
app.register_blueprint(paping_blueprint)
app.register_blueprint(mtr_blueprint)
app.register_blueprint(axios_blueprint)
app.register_blueprint(show_papaing_or_mtr_result_by_querying_apache_blueprint)
app.register_blueprint(dig_blueprint)
app.register_blueprint(curl_blueprint)
app.register_blueprint(http_ping_blueprint)
app.register_blueprint(customized_command_blueprint)

from blueprint_paping.whitelist_blueprint import whitelist_blueprint
app.register_blueprint(whitelist_blueprint)

from blueprint_paping.sse_blueprint import sse_blueprint
app.register_blueprint(sse_blueprint)

from model import db, b11_huck_ge_probes

from flask_migrate import Migrate
from flask_cors import CORS, cross_origin
migrate = Migrate(app, db)
from config import DevConfig
app.config.from_object(DevConfig)
CORS(app)

db.init_app(app)

######################session control#########################################
from flask import session
app.secret_key = os.urandom(24)

#to insert time into the session
from datetime import datetime


#####################Run Flask##################################################


######################################################################
# check if the user value is in the session dictionary
@app.route('/read_session')
def get_session():
    if "user" in session:
        return "in route read session, your session is %s" % (session["user"])
    return "You're not logged in"


######################################################################
@app.route('/dropsession')
def dropsession():
    session.pop('user', None)  #clear the session first, so that
    return 'Session Clear'

######################################################################
@app.route('/make_sure_backend_is_alive')
@app.route('/make_sure_backend_is_alive/')
def make_sure_backend_is_alive():
    return 'Iam alive'
