import json
import random
from abc import abstractmethod
from time import sleep
import paho.mqtt.client as mqtt


class Sensor:
    IP = "localhost"
    sensor = None
    topic = "piante"

    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.sensor = mqtt.Client()
        self.sensor.connect(self.IP, 1883, 60)

    @abstractmethod
    def publish(self):
        pass


class HumiditySensor(Sensor):
    humidity = 50

    def publish(self):
        self.humidity += random.randint(-1,1)
        payload = {
            'name': self.name,
            'type': self.type,
            'humidity': self.humidity
        }
        self.sensor.publish(self.topic + "/humidity", json.JSONEncoder().encode(payload))


class TemperatureSensor(Sensor):
    temperature = 25

    def publish(self):
        self.temperature += random.randint(-1,1)
        payload = {
            'name': self.name,
            'type': self.type,
            'temperature': self.temperature
        }
        self.sensor.publish(self.topic + "/temperature", json.JSONEncoder().encode(payload))


class Plant:

    def __init__(self, type, name):
        self.type = type
        self.name = name
        self.humidity_sensor = HumiditySensor(self.name, self.type)
        self.temperature_sensor = TemperatureSensor(self.name, self.type)

    def update(self):
        self.humidity_sensor.publish()
        self.temperature_sensor.publish()


pianta1 = Plant("limone","pianta1")
pianta2 = Plant("orchidea","pianta2")
piante = [pianta1,pianta2]

while True:
    #print("in while")
    for pianta in piante:
        pianta.update()
    sleep(5)