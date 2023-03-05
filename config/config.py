import json
from threading import Thread

import requests
from flask import Flask
from flask import jsonify

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.secret_key = 'B;}}S5Cx@->^^"hQT{T,GJ@YI*><17'


@app.route("/config/sensors/<measurement>", methods=["GET"])
def get_sensors(measurement):
    with open('config.json', 'r') as f:
        sensors = json.loads(f.read())['sensors']

    resp = jsonify(success=True, error="none", data=sensors[measurement])
    resp.status_code = 200
    return resp


@app.route("/config/thresholds/<measurement>", methods=["GET"])
def get_thresholds(measurement):
    with open('config.json', 'r') as f:
        thresholds = json.loads(f.read())['thresholds']

    resp = jsonify(success=True, error="none", data=thresholds[measurement])
    resp.status_code = 200
    return resp


if __name__ == "__main__":
    app.run(debug=True, host='config', port=5008)
