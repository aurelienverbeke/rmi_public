import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from importlib.resources import files

import pandas as pd
from flask import Flask, redirect, render_template, request, send_file
from tornado.process import CalledProcessError

from viscalmon.general.io.radar import get_files_names
from viscalmon.viewer.create_images import create_images

app = Flask(__name__, static_folder=os.environ["DIR_VIEWER_STATIC"], static_url_path="/static")





# Configure logger
logger = logging.getLogger(app.name)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)





@app.route('/favicon.ico')
def favicon():
    return send_file(str(files("viscalmon.viewer").joinpath("ppi.png")))



@app.route("/pos/<radar>")
def pos(radar : str):
    csv_path = files("viscalmon.general").joinpath("radar_pos.csv")
    with csv_path.open("r") as f:
        pos_df = pd.read_csv(f)
    if radar in pos_df["radar"].values:
        pos = pos_df[pos_df["radar"]==radar].iloc[0]
        return ({ "lat":pos["lat"], "lon":pos["lon"], "alt":pos["alt"] })
    else:
        return ("", 400)



@app.route("/intervals/<image_type>")
def intervals(image_type : str):
    if image_type == "ppi":
        folders = os.listdir(os.environ["DIR_PPI"])
    elif image_type == "azi-dist":
        folders = os.listdir(os.environ["DIR_AZI_DIST"])
    else:
        return ("", 400)

    intervals = [ datetime.strptime(folder[:12], "%Y%m%d%H%M").replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M") + " -> " + datetime.strptime(folder[13:], "%Y%m%d%H%M").replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M") for folder in folders ]

    return dict(zip(folders, intervals))



@app.route("/add/<image_type>", methods=["POST"])
def add(image_type : str):
    if image_type not in ["ppi", "azi-dist"]:
        return ("", 400)

    radars = []
    if request.json["jabbeke"]:
        radars.append("jabbeke")
    if request.json["wideumont"]:
        radars.append("wideumont")
    start_timestamp = datetime.strptime(request.json["start_date"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    end_timestamp = datetime.strptime(request.json["end_date"], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    moments = []
    if request.json["dbz"]:
        moments.append("dBZ")
    if request.json["dbuz"]:
        moments.append("dBuZ")
    if request.json["phidp"]:
        moments.append("PhiDP")
    if request.json["uphidp"]:
        moments.append("uPhiDP")
    if request.json["rhohv"]:
        moments.append("RhoHV")
    if request.json["zdr"]:
        moments.append("ZDR")
    if request.json["kdp"]:
        moments.append("KDP")
    if request.json["v"]:
        moments.append("V")

    for radar in radars:
        if image_type == "ppi":
            app.logger.info(f"vol:{",".join(moments)}")
            files = get_files_names(f"vol:{",".join(moments)}", start_timestamp, end_timestamp, radar)
            create_images(radar, start_timestamp, end_timestamp, files, "ppi")
        else:
            files = get_files_names(f"azi:{",".join(moments)}", start_timestamp, end_timestamp, radar)
            create_images(radar, start_timestamp, end_timestamp, files, "azidist")
    
    return ("", 200)



@app.route("/dir-size/<image_type>")
def dir_size(image_type : str):
    try:
        if image_type == "ppi":
            return subprocess.run(["du", "-sh", os.environ["DIR_PPI"]], capture_output=True, text=True, check=True).stdout.strip(" \n").split("\t")[0]
        elif image_type == "azi-dist":
            return subprocess.run(["du", "-sh", os.environ["DIR_AZI_DIST"]], capture_output=True, text=True, check=True).stdout.strip(" \n").split("\t")[0]
    except CalledProcessError:
        return ("", 500)

    return ("", 400)

    
    
@app.route('/ppi')
def ppi():
    colormaps = files("viscalmon.viewer").joinpath("colormaps.json")
    with colormaps.open("r") as f_colormaps:
        colormaps = json.load(f_colormaps)
    return render_template("ppi.html", colormaps=colormaps, static_folder=os.environ["SUBDIR_PPI"])



@app.route('/azi-dist')
def azi_dist():
    colormaps = files("viscalmon.viewer").joinpath("colormaps.json")
    with colormaps.open("r") as f_colormaps:
        colormaps = json.load(f_colormaps)
    return render_template("azi_dist.html", colormaps=colormaps, static_folder=os.environ["SUBDIR_AZI_DIST"])



@app.route('/')
def index():
    return redirect("/ppi")



if __name__ == "__main__":
    app.run(debug=True)
