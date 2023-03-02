import math
import random
from abc import abstractmethod
import datetime
from threading import Thread
from time import sleep

import paho.mqtt.client as mqtt
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

        for i in range(1, 5):
            soil_moist_sens = self.SoilMoistureSensor(id=counter, type='moisture', outer=self, plant_id=i)
            self.sensors.append(soil_moist_sens)
            counter += 1

        for i in range(1, 5):
            temp_sens = self.TemperatureSensor(id=counter, type='temperature', outer=self)
            self.sensors.append(temp_sens)
            counter += 1

        for i in range(1, 5):
            humidity_sens = self.AirHumiditySensor(id=counter, type='humidity', outer=self)
            self.sensors.append(humidity_sens)
            counter += 1

        self.sensors.append(self.LightSensor(id=counter, type='light', outer=self))

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


if __name__ == '__main__':
    gr = Greenhouse(temperature=23, humidity=50)
