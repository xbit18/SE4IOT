import math
from tenacity import retry
import random
from abc import abstractmethod
import datetime
from threading import Thread
from time import sleep

import paho.mqtt.client as mqtt
import requests
from numpy import interp


class Greenhouse:
    light = 0

    def __init__(self, temperature, humidity):

        # initialize default values for humidity and temperature
        self.humidity = humidity
        self.temperature = temperature

        # create sensors list
        self.sensors = []

        # create mqtt client for publishing and subscribing
        self.client = mqtt.Client()

        # create thread for mqtt initialization to avoid blocking loop
        thread = Thread(target=self.initialize_mqtt)
        thread.start()

        # creation of sensors
        counter = 1

        for measurement in ["temperature","humidity","moisture","light"]:
            n = requests.get(f"http://config:5008/config/sensors/{measurement}").json()['data']
            for i in range(1, n+1):
                if measurement == "temperature":
                    temp_sens = self.TemperatureSensor(id=counter, type='temperature', outer=self)
                    self.sensors.append(temp_sens)
                elif measurement == "humidity":
                    humidity_sens = self.AirHumiditySensor(id=counter, type='humidity', outer=self)
                    self.sensors.append(humidity_sens)
                elif measurement == "moisture":
                    soil_moist_sens = self.SoilMoistureSensor(id=counter, type='moisture', outer=self, plant_id=i)
                    self.sensors.append(soil_moist_sens)
                elif measurement == "light":
                    light_sensor = self.LightSensor(id=counter, type='light', outer=self)
                    self.sensors.append(light_sensor)
                counter += 1

        self.run()

    def initialize_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect('mosquitto', 1883, 60)
        self.client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe('activate/#')
        print(f"Greenhouse connected and listening")

    # activate/<data-type>/<action> e.g. temperature/increase for non specific measurement
    # activate/<data-type>/<action>/<plant> e.g. moisture/increase/2
    def on_message(self, client, userdata, msg):
        topic_split = str(msg.topic).split('/')

        if topic_split[1] == 'temperature':
            print(f"Message received {msg.topic} - {msg.payload.decode('utf-8')}")
            if topic_split[2] == 'increase':
                self.temperature += 2
            elif topic_split[2] == 'decrease':
                self.temperature -= 2
        elif topic_split[1] == 'humidity':
            print(f"Message received {msg.topic} - {msg.payload.decode('utf-8')}")
            if topic_split[2] == 'increase':
                self.humidity += 10
            elif topic_split[2] == 'decrease':
                self.humidity -= 10
        elif topic_split[1] == 'moisture':
            for sensor in self.sensors:
                if isinstance(sensor, self.SoilMoistureSensor) and sensor.plant_id == int(topic_split[3]):
                    print(f"Message received {msg.topic} - {msg.payload.decode('utf-8')}")
                    if topic_split[2] == 'increase':
                        sensor.moisture += 10
                    elif topic_split[2] == 'decrease':
                        sensor.moisture -= 10
        elif topic_split[1] == 'light':
            for sensor in self.sensors:
                if isinstance(sensor, self.LightSensor):
                    if topic_split[2] == 'on':
                        sensor.light_on = True
                    else:
                        sensor.light_on = False

    def run(self):
        while True:
            for sensor in self.sensors:
                data = sensor.get_publish_data()
                topic = data[0]
                payload = data[1]
                self.client.publish(topic, payload)
            sleep(5)

    class Sensor:

        def __init__(self, id, type, outer):
            self.id = id
            self.type = type
            self.outer = outer

        @abstractmethod
        def get_publish_data(self):
            pass

    class SoilMoistureSensor(Sensor):

        def __init__(self, id, plant_id, type, outer):
            super().__init__(id, type, outer)
            self.plant_id = plant_id
            self.moisture = 50

        def get_publish_data(self):
            # Randomly changes the actual temperature of the greenhouse with probability 0.1
            rand = random.randint(1, 10)
            if rand == 1:
                self.moisture += random.randint(-1, 1)

            return f"moisture/{self.id}/{self.plant_id}", self.moisture

    class AirHumiditySensor(Sensor):

        def get_publish_data(self):
            # Randomly changes the actual temperature of the greenhouse with probability 0.1
            rand = random.randint(1, 10)
            if rand == 1:
                self.outer.humidity += random.randint(-1, 1)

            return f"humidity/{self.id}", self.outer.humidity + random.randint(-1, 1)

    class TemperatureSensor(Sensor):

        def get_publish_data(self):
            # Randomly changes the actual temperature of the greenhouse with probability 0.1
            rand = random.randint(1, 10)
            if rand == 1:
                self.outer.temperature += random.randint(-1, 1)

            return f"temperature/{self.id}", self.outer.temperature + random.randint(-1, 1)

    class LightSensor(Sensor):
        light_on = False
        def get_publish_data(self):
            if self.light_on:
                self.outer.light = 255
            else:
                self.outer.light = self.getLightValue()

            return f"light/{self.id}", self.outer.light

        def getLightValue(self):
            hour = datetime.datetime.now().hour

            minute = datetime.datetime.now().minute

            value = hour * 60 + minute  # 0 - 1440

            mapped_value = interp(value, [0, 1440], [0, 360])

            sin = math.sin(math.radians(mapped_value) + math.pi * (3 / 2))

            light_value = interp(sin, [-1, 1], [0, 255])

            rand = random.randint(0, 4)  # 0.2 probability of oscillating around function

            if rand == 0:
                value = light_value + random.randint(-10, 10)
                if value < 0:  # value can't be negative
                    value = 0
                if value > 255:  # value can't be negative
                    value = 255
            else:
                value = light_value
            return value


@retry
def init_flows():
    moist_sens = requests.get(f"http://config:5008/config/sensors/moisture").json()['data']

    flow_id = ""
    check_flow = requests.get(f"http://nodered:1880/flows").json()

    for flow in check_flow:
        # se il flow esiste, mi prendo l'id per usarlo dopo
        if flow['type'] == "tab":
            if flow['label'] == "Moisture":
                flow_id = flow["id"]
                response = requests.delete(f"http://nodered:1880/flow/{flow['id']}")
                break

    nodes = []
    configs = []
    x = 100
    y = 60
    for i in range(1, moist_sens + 1):
        ui_group = {
            "id": f"uigroup{i}",
            "type": "ui_group",
            "name": f"Moisture of Plant {i}",
            "tab": "b95bdcd246960f21",
            "order": 3,
            "disp": True,
            "width": "18",
            "collapse": False,
            "className": ""
        }
        configs.append(ui_group)

        wave = {
            "id": f"wave{i}",
            "type": "ui_gauge",
            "z": flow_id,
            "name": "",
            "group": f"uigroup{i}",
            "order": 1,
            "width": "6",
            "height": "6",
            "gtype": "wave",
            "title": "",
            "label": "%",
            "format": "{{value}}",
            "min": 0,
            "max": "100",
            "colors": [
                "#b30000",
                "#00b500",
                "#b30000"
            ],
            "seg1": "50",
            "seg2": "80",
            "diff": False,
            "className": "",
            "x": 590,
            "y": y,
            "wires": []
        }
        nodes.append(wave)
        plant = {
            "id": f"plant{i}",
            "type": "ui_gauge",
            "z": flow_id,
            "name": "",
            "group": "df0de8f973aaf073",
            "order": 2,
            "width": 5,
            "height": 5,
            "gtype": "wave",
            "title": f"Plant {i}",
            "label": "%",
            "format": "{{value}}",
            "min": 0,
            "max": "100",
            "colors": [
                "#b30000",
                "#00b500",
                "#b30000"
            ],
            "seg1": "50",
            "seg2": "80",
            "diff": False,
            "className": "",
            "x": 600,
            "y": y + 40,
            "wires": []
        }
        nodes.append(plant)
        template = {
            "id": f"template{i}",
            "type": "ui_template",
            "z": flow_id,
            "group": f"uigroup{i}",
            "name": f"template{i}",
            "order": 2,
            "width": "12",
            "height": "8",
            "format": f"<div style=\"border-radius: 10px; width: 100%; height: 100%; overflow: hidden;\">\n    <iframe src=\"http://localhost:3000/d-solo/47Y9EaJVz/new-dashboard?orgId=1&refresh=5s&theme=dark&panelId={i + 3}\"\n    width=\"100%\" height=\"100%\" frameborder=\"0\"></iframe>\n</div>",
            "storeOutMessages": True,
            "fwdInMessages": True,
            "resendOnRefresh": True,
            "templateScope": "local",
            "className": "",
            "x": 600,
            "y": y - 40,
            "wires": [
                []
            ]
        }
        nodes.append(template)

        function = {
            "id": f"function{i}",
            "type": "function",
            "z": flow_id,
            "name": f"function{i}",
            "func": "var payload = msg.payload\nvar sum = 0\nvar counter = 0\nfor (let index = 0; index < payload.length; index++) {\n    const element = payload[index]['_value'];\n    sum = sum + element;\n    counter = counter + 1\n}\nmsg.payload = (sum/counter) | 0\nmsg.debug = { '1': msg.payload }\nreturn msg;",
            "outputs": 1,
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 410,
            "y": y,
            "wires": [
                [
                    f"plant{i}",
                    f"wave{i}"
                ]
            ]
        }
        nodes.append(function)

        query = {
            "id": f"query{i}",
            "type": "influxdb in",
            "z": "cf0f97c5422f9808",
            "influxdb": "f31dede1f911c00f",
            "name": f"query{i}",
            "query": f"from(bucket: \"iot\")\n  |> range(start: -1m)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"moisture\")\n  |> filter(fn: (r) => r[\"_field\"] == \"value\")\n  |> filter(fn: (r) => r[\"plant_id\"] == \"{i}\")\n  |> sort(columns: [\"_time\"], desc: true)",
            "rawOutput": False,
            "precision": "",
            "retentionPolicy": "",
            "org": "univaq",
            "x": 240,
            "y": y,
            "wires": [
                [
                    f"function{i}"
                ]
            ]
        }
        nodes.append(query)

        button_plus = {
            "id": f"button_plus{i}",
            "type": "ui_button",
            "z": "cf0f97c5422f9808",
            "name": "",
            "group": f"uigroup{i}",
            "order": 3,
            "width": "3",
            "height": "2",
            "passthru": False,
            "label": "+10%",
            "tooltip": "",
            "color": "",
            "bgcolor": "#50bf6e",
            "className": "",
            "icon": "fa-arrow-up",
            "payload": "",
            "payloadType": "str",
            "topic": f"waterpump/increase/{i}",
            "topicType": "str",
            "x": 170,
            "y": y + 800,
            "wires": [
                [
                    "mqtt_out"
                ]
            ]
        }
        button_minus = {
            "id": f"button_minus{i}",
            "type": "ui_button",
            "z": "cf0f97c5422f9808",
            "name": "",
            "group": f"uigroup{i}",
            "order": 4,
            "width": "3",
            "height": "2",
            "passthru": False,
            "label": "-10%",
            "tooltip": "",
            "color": "",
            "bgcolor": "#bf5050",
            "className": "",
            "icon": "fa-arrow-down",
            "payload": "",
            "payloadType": "str",
            "topic": f"waterpump/decrease/{i}",
            "topicType": "str",
            "x": 170,
            "y": y + 850,
            "wires": [
                [
                    "mqtt_out"
                ]
            ]
        }
        nodes.append(button_plus)
        nodes.append(button_minus)
        y += 150

    mqtt_out = {
        "id": "mqtt_out",
        "type": "mqtt out",
        "z": "cf0f97c5422f9808",
        "name": "",
        "topic": "",
        "qos": "",
        "retain": "",
        "respTopic": "",
        "contentType": "",
        "userProps": "",
        "correl": "",
        "expiry": "",
        "broker": "263cb68dcd37c7d7",
        "x": 610,
        "y": (y + 1000) / 2,
        "wires": []
    }

    nodes.append(mqtt_out)

    inject = {
        "id": "inject",
        "type": "inject",
        "z": "cf0f97c5422f9808",
        "name": "",
        "props": [],
        "repeat": "1",
        "crontab": "",
        "once": False,
        "onceDelay": 0.1,
        "topic": "",
        "x": 90,
        "y": y / 2,
        "wires": [
            [f"query{i}" for i in range(1, moist_sens + 1)]
        ]
    }

    nodes.append(inject)
    print(nodes)

    flow = {
        "type": "tab",
        "label": "Moisture",
        "nodes": nodes,
        "configs": configs,
        "disabled": False,
        "info": "",
        "env": []
    }

    add_flow = requests.post(f"http://nodered:1880/flow", json=flow)
    print(add_flow.text)

@retry
def init_grafana():
    key = "eyJrIjoiblVOcUZvckxIRHE3enFQUng2M3dRQXpOR2ZOQnNoT24iLCJuIjoiaW90IiwiaWQiOjF9"

    panels = [
        {
            "datasource": {
                "type": "influxdb",
                "uid": "OI-rhbJVz"
            },
            "description": "",
            "fieldConfig": {
                "defaults": {
                    "color": {
                        "mode": "palette-classic"
                    },
                    "custom": {
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line",
                        "fillOpacity": 0,
                        "gradientMode": "none",
                        "hideFrom": {
                            "legend": False,
                            "tooltip": False,
                            "viz": False
                        },
                        "lineInterpolation": "smooth",
                        "lineWidth": 2,
                        "pointSize": 5,
                        "scaleDistribution": {
                            "type": "linear"
                        },
                        "showPoints": "never",
                        "spanNulls": False,
                        "stacking": {
                            "group": "A",
                            "mode": "none"
                        },
                        "thresholdsStyle": {
                            "mode": "off"
                        }
                    },
                    "decimals": 0,
                    "mappings": [],
                    "max": 255,
                    "min": 0,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            },
                            {
                                "color": "red",
                                "value": 80
                            }
                        ]
                    }
                },
                "overrides": []
            },
            "gridPos": {
                "h": 8,
                "w": 12,
                "x": 0,
                "y": 0
            },
            "id": 1,
            "options": {
                "legend": {
                    "calcs": [],
                    "displayMode": "list",
                    "placement": "bottom",
                    "showLegend": False
                },
                "tooltip": {
                    "mode": "single",
                    "sort": "none"
                }
            },
            "targets": [
                {
                    "datasource": {
                        "type": "influxdb",
                        "uid": "OI-rhbJVz"
                    },
                    "query": "from(bucket: \"iot\")\n  |> range(start: -1h)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"light\")\n  |> filter(fn: (r) => r[\"_field\"] == \"value\")\n  |> sort(columns: [\"_time\"], desc: true)",
                    "refId": "A"
                }
            ],
            "type": "timeseries"
        },
        {
            "datasource": {
                "type": "influxdb",
                "uid": "OI-rhbJVz"
            },
            "description": "",
            "fieldConfig": {
                "defaults": {
                    "color": {
                        "mode": "palette-classic"
                    },
                    "custom": {
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line",
                        "fillOpacity": 0,
                        "gradientMode": "none",
                        "hideFrom": {
                            "legend": False,
                            "tooltip": False,
                            "viz": False
                        },
                        "lineInterpolation": "smooth",
                        "lineStyle": {
                            "fill": "solid"
                        },
                        "lineWidth": 2,
                        "pointSize": 1,
                        "scaleDistribution": {
                            "type": "linear"
                        },
                        "showPoints": "auto",
                        "spanNulls": False,
                        "stacking": {
                            "group": "A",
                            "mode": "none"
                        },
                        "thresholdsStyle": {
                            "mode": "off"
                        }
                    },
                    "mappings": [],
                    "max": 50,
                    "min": 0,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            }
                        ]
                    },
                    "unit": "celsius"
                },
                "overrides": [
                    {
                        "matcher": {
                            "id": "byName",
                            "options": "value 10"
                        },
                        "properties": [
                            {
                                "id": "color",
                                "value": {
                                    "fixedColor": "green",
                                    "mode": "fixed"
                                }
                            }
                        ]
                    }
                ]
            },
            "gridPos": {
                "h": 9,
                "w": 12,
                "x": 12,
                "y": 8
            },
            "id": 2,
            "options": {
                "legend": {
                    "calcs": [],
                    "displayMode": "list",
                    "placement": "bottom",
                    "showLegend": False
                },
                "tooltip": {
                    "mode": "single",
                    "sort": "none"
                }
            },
            "targets": [
                {
                    "datasource": {
                        "type": "influxdb",
                        "uid": "OI-rhbJVz"
                    },
                    "query": "from(bucket: \"iot\")\n  |> range(start: -5m)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"temperature\")\n  |> yield(name: \"mean\")",
                    "refId": "A"
                }
            ],
            "type": "timeseries"
        },
        {
            "datasource": {
                "type": "influxdb",
                "uid": "OI-rhbJVz"
            },
            "fieldConfig": {
                "defaults": {
                    "color": {
                        "mode": "palette-classic"
                    },
                    "custom": {
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line",
                        "fillOpacity": 0,
                        "gradientMode": "none",
                        "hideFrom": {
                            "legend": False,
                            "tooltip": False,
                            "viz": False
                        },
                        "lineInterpolation": "smooth",
                        "lineStyle": {
                            "fill": "solid"
                        },
                        "lineWidth": 2,
                        "pointSize": 1,
                        "scaleDistribution": {
                            "type": "linear"
                        },
                        "showPoints": "auto",
                        "spanNulls": False,
                        "stacking": {
                            "group": "A",
                            "mode": "none"
                        },
                        "thresholdsStyle": {
                            "mode": "off"
                        }
                    },
                    "mappings": [],
                    "max": 100,
                    "min": 0,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            }
                        ]
                    },
                    "unit": "humidity"
                },
                "overrides": [
                    {
                        "matcher": {
                            "id": "byName",
                            "options": "value 10"
                        },
                        "properties": [
                            {
                                "id": "color",
                                "value": {
                                    "fixedColor": "green",
                                    "mode": "fixed"
                                }
                            }
                        ]
                    }
                ]
            },
            "gridPos": {
                "h": 9,
                "w": 12,
                "x": 0,
                "y": 16
            },
            "id": 3,
            "options": {
                "legend": {
                    "calcs": [],
                    "displayMode": "list",
                    "placement": "bottom",
                    "showLegend": False
                },
                "tooltip": {
                    "mode": "single",
                    "sort": "none"
                }
            },
            "targets": [
                {
                    "datasource": {
                        "type": "influxdb",
                        "uid": "OI-rhbJVz"
                    },
                    "query": "from(bucket: \"iot\")\n  |> range(start: -5m)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"humidity\")\n  |> yield(name: \"mean\")",
                    "refId": "A"
                }
            ],
            "type": "timeseries"
        }
    ]

    n = requests.get(f"http://config:5008/config/sensors/moisture").json()['data']
    for i in range(1, n + 1):
        moisture_panel = {
            "datasource": {
                "type": "influxdb",
                "uid": "OI-rhbJVz"
            },
            "description": "",
            "fieldConfig": {
                "defaults": {
                    "color": {
                        "fixedColor": "blue",
                        "mode": "fixed"
                    },
                    "custom": {
                        "axisCenteredZero": False,
                        "axisColorMode": "text",
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line",
                        "fillOpacity": 0,
                        "gradientMode": "none",
                        "hideFrom": {
                            "legend": False,
                            "tooltip": False,
                            "viz": False
                        },
                        "lineInterpolation": "smooth",
                        "lineWidth": 2,
                        "pointSize": 5,
                        "scaleDistribution": {
                            "type": "linear"
                        },
                        "showPoints": "never",
                        "spanNulls": False,
                        "stacking": {
                            "group": "A",
                            "mode": "none"
                        },
                        "thresholdsStyle": {
                            "mode": "off"
                        }
                    },
                    "mappings": [],
                    "max": 100,
                    "min": 0,
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            }
                        ]
                    },
                    "unit": "%"
                },
                "overrides": []
            },
            "gridPos": {
                "h": 8,
                "w": 12,
                "x": 12,
                "y": 0
            },
            "id": i + 3,
            "options": {
                "legend": {
                    "calcs": [],
                    "displayMode": "list",
                    "placement": "bottom",
                    "showLegend": False
                },
                "tooltip": {
                    "mode": "single",
                    "sort": "none"
                }
            },
            "pluginVersion": "9.3.6",
            "targets": [
                {
                    "datasource": {
                        "type": "influxdb",
                        "uid": "OI-rhbJVz"
                    },
                    "query": f"from(bucket: \"iot\")\n  |> range(start: -1m)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"moisture\")\n  |> filter(fn: (r) => r[\"_field\"] == \"value\")\n  |> filter(fn: (r) => r[\"plant_id\"] == \"{i}\")\n  |> yield(name: \"mean\")",
                    "refId": "A"
                }
            ],
            "title": f"Plant {i} Soil Moisture",
            "type": "timeseries"
        }

        panels.append(moisture_panel)

    dashboard = {"dashboard":
        {
            "annotations": {
                "list": [
                    {
                        "builtIn": 1,
                        "datasource": {
                            "type": "grafana",
                            "uid": "-- Grafana --"
                        },
                        "enable": True,
                        "hide": True,
                        "iconColor": "rgba(0, 211, 255, 1)",
                        "name": "Annotations & Alerts",
                        "target": {
                            "limit": 100,
                            "matchAny": False,
                            "tags": [],
                            "type": "dashboard"
                        },
                        "type": "dashboard"
                    }
                ]
            },
            "editable": True,
            "fiscalYearStartMonth": 0,
            "graphTooltip": 0,
            "id": 1,
            "links": [],
            "liveNow": False,
            "panels": panels,
            "refresh": "5s",
            "schemaVersion": 37,
            "style": "dark",
            "tags": [],
            "templating": {
                "list": []
            },
            "time": {
                "from": "now-1m",
                "to": "now"
            },
            "timepicker": {},
            "timezone": "",
            "title": "New dashboard",
            "uid": "47Y9EaJVz",
            "version": 11,
            "weekStart": ""
        },
        "message": "Created panels dynamically",
        "overwrite": True
    }
    headers = {"Authorization": f"Bearer {key}"}
    post = requests.post("http://grafana:3000/api/dashboards/db", json=dashboard, headers=headers)
    print(post.text)
if __name__ == '__main__':
    init_grafana()
    init_flows()
    gr = Greenhouse(temperature=23, humidity=50)
