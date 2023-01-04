import json

import paho.mqtt.client as mqtt

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("piante/#")

# The callback for when a publish message is received from the server.
def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    plant = json.JSONDecoder().decode(payload)
    if msg.topic == "piante/humidity":
        print(f'Nome: {plant["name"]}, Tipo: {plant["type"]}, Umidità: {plant["humidity"]}')
    else:
        print(f'Nome: {plant["name"]}, Tipo: {plant["type"]}, Temperatura: {plant["temperature"]}')


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()