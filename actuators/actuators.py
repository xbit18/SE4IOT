import random
from abc import abstractmethod, ABC
from time import sleep
from threading import Thread
import paho.mqtt.client as mqtt


def main():
    for i in range(1, 5):
        water_pump = WaterPump(i)

    conditioner = Conditioner()
    humidifier = AirHumidifier()
    light = Light()


class Actuator(ABC):

    def __init__(self):
        self.client = mqtt.Client()
        thread = Thread(target=self.initialize_mqtt)
        thread.start()

    def initialize_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect('172.20.0.100', 1883, 60)
        self.client.loop_forever()

    @abstractmethod
    def on_connect(self, client, userdata, flags, rc):
        pass

    # <actuator>/<action> e.g. conditioner/increase
    # <actuator>/<action>/<plant> e.g. pump/increase/2
    @abstractmethod
    def on_message(self, client, userdata, msg):
        pass

    def increase(self):
        pass

    def decrease(self):
        pass


class Conditioner(Actuator):

    def increase(self):
        print(f'Increasing temperature')
        self.client.publish('activate/temperature/increase')

    def decrease(self):
        print(f'Decreasing temperature')
        self.client.publish('activate/temperature/decrease')

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe('conditioner/#')
        print(f"Conditioner connected and listening")

    def on_message(self, client, userdata, msg):
        print(f"Message received {msg.topic}")
        topic_split = str(msg.topic).split('/')

        if topic_split[1] == 'increase':
            self.increase()
        elif topic_split[1] == 'decrease':
            self.decrease()


class WaterPump(Actuator):

    def __init__(self, plant_id):
        super().__init__()
        self.plant_id = plant_id

    def increase(self):
        print(f'Increasing moisture of plant {self.plant_id}')
        self.client.publish(f'activate/moisture/increase/{self.plant_id}')

    def decrease(self):
        print(f'Decreasing moisture of plant {self.plant_id}')
        self.client.publish(f'activate/moisture/decrease/{self.plant_id}')

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe(f'waterpump/+/{self.plant_id}')
        print(f"Pump {self.plant_id} connected and listening")

    def on_message(self, client, userdata, msg):
        print(f"Message received {msg.topic}")
        topic_split = str(msg.topic).split('/')
        if topic_split[1] == 'increase':
            self.increase()
        elif topic_split[1] == 'decrease':
            self.decrease()


class AirHumidifier(Actuator):

    def increase(self):
        print(f'Increasing humidity')
        self.client.publish(f'activate/humidity/increase')

    def decrease(self):
        print(f'Decreasing humidity')
        self.client.publish(f'activate/humidity/decrease')

    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe('humidifier/#')
        print(f"Humidifier connected and listening")

    def on_message(self, client, userdata, msg):
        print(f"Message received {msg.topic}")
        topic_split = str(msg.topic).split('/')

        if topic_split[1] == 'increase':
            self.increase()
        elif topic_split[1] == 'decrease':
            self.decrease()

class Light(Actuator):
    def on_connect(self, client, userdata, flags, rc):
        self.client.subscribe('lightbulb')
        print(f"Light connected and listening")

    def on_message(self, client, userdata, msg):
        print(f"Message received {msg.topic}")

        payload = bytes.decode(msg.payload)
        if payload == 'true':
            self.on()
        elif payload == 'false':
            self.off()

    def on(self):
        print(f'Light on')
        self.client.publish(f'activate/light/on')
    def off(self):
        print(f'Light off')
        self.client.publish(f'activate/light/off')

if __name__ == '__main__':
    main()
