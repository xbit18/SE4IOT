import json
import random
import time
from abc import abstractmethod
from hashlib import sha1, sha256
from time import sleep
from threading import Thread

import paho.mqtt.client as mqtt


class Sensors:
    sensors = []

    def __init__(self):
        hum_sens_1 = self.HumiditySensor(1, 1)
        hum_sens_2 = self.HumiditySensor(2, 2)
        temp_sens_1 = self.TemperatureSensor(3, 1)
        temp_sens_2 = self.TemperatureSensor(4, 2)
        self.sensors = [hum_sens_1, hum_sens_2, temp_sens_1, temp_sens_2]
        thread = Thread(target=self.run)
        thread.start()


    class Sensor:
        IP = "localhost"
        sensor = None

        def __init__(self, id, plant_id):
            self.id = id
            self.plant_id = plant_id
            self.sensor = mqtt.Client()
            self.sensor.connect(self.IP, 1883, 60)

        @abstractmethod
        def publish(self):
            pass

    class HumiditySensor(Sensor):
        humidity = 50

        def publish(self):
            self.humidity += random.randint(-1, 1)
            self.sensor.publish(f"/humidity/{self.plant_id}/{self.id}", self.humidity)

    class TemperatureSensor(Sensor):
        temperature = 25

        def publish(self):
            self.temperature += random.randint(-1, 1)
            self.sensor.publish(f"/temperature/{self.plant_id}/{self.id}", self.temperature)

    def run(self):
        while True:
            for sensor in self.sensors:
                sensor.publish()
            sleep(5)


