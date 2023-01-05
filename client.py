import json
from errno import errorcode
from threading import Thread

import mysql.connector
import paho.mqtt.client as mqtt

class Client:
    config = {
        'user': 'admin',
        'password': 'Sfratis1',
        'host': 'iot.cn5dhjjs7sxc.eu-west-3.rds.amazonaws.com',
        'database': 'iot',
        'raise_on_warnings': True
    }
    def __init__(self):
        client = mqtt.Client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect("localhost", 1883, 60)
        client.loop_forever()
        thread = Thread(target=self.run)
        thread.start()

    def create_plant(self, plant_id, cursor):
        check_plant_exists = ("SELECT * FROM plants WHERE id = %s")
        cursor.execute(check_plant_exists, (plant_id,))
        row = cursor.fetchone()

        try:
            # Se pianta non esiste la creo
            if row == None:
                insert_new_plant = ("INSERT INTO plants (id, name, species) VALUES (%s, %s, %s)")
                cursor.execute(insert_new_plant, (plant_id, "", ""))
                print("Plant created")
            return 1
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return 0

    def create_sensor(self, sensor_id, plant_id, data_type, cursor):
        check_sensor_exists = ("SELECT * FROM sensors WHERE id = %s")
        cursor.execute(check_sensor_exists, (sensor_id,))
        row = cursor.fetchone()

        try:
            # Se sensore non esiste
            if row == None:
                insert_new_sensor = ("INSERT INTO sensors (id, type, plant_id) VALUES (%s, %s, %s)")
                cursor.execute(insert_new_sensor, (sensor_id, data_type, plant_id))
                print("Sensor created")
            return 1
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return 0
    def insert_value(self, payload, data_type, plant_id, cursor):
        try:
            if data_type == "humidity":
                insert_new_data = ("INSERT INTO humidity (plant_id, humidity) VALUES (%s,%s)")
            else:
                insert_new_data = ("INSERT INTO temperature (plant_id, temperature) VALUES (%s,%s)")
            cursor.execute(insert_new_data, (plant_id, payload))
            print(f"Data added")
            return 1
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return 0

    def on_connect(self, client, userdata, flags, rc):
        print("Connected to Mosquitto")
        client.subscribe("humidity/#")
        client.subscribe("temperature/#")


    # The callback for when a publish message is received from the server.
    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8')
        topic = str(msg.topic)
        topic_split = topic.split('/')

        data_type = topic_split[0]
        plant_id = topic_split[1]
        sensor_id = topic_split[2]

        cnx = mysql.connector.connect(**self.config)
        cursor = cnx.cursor()
        cursor.execute("USE iot")

        plant = self.create_plant(plant_id, cursor)
        sensor = self.create_sensor(sensor_id, plant_id, data_type, cursor)
        data = self.insert_value(payload, data_type, plant_id, cursor)
        success = plant + sensor + data
        if success >= 3:
            cnx.commit()
        else:
            raise Exception("Something went wrong")
