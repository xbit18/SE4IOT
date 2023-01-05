import sensors
import client
import mysql.connector
from mysql.connector import errorcode

config = {
    'user': 'admin',
    'password': 'Sfratis1',
    'host': 'iot.cn5dhjjs7sxc.eu-west-3.rds.amazonaws.com',
    'database': 'iot',
    'raise_on_warnings': True
}

TABLES = {}

TABLES['plants'] = (
    "CREATE TABLE if not exists `plants` ("
    "  `id` int NOT NULL AUTO_INCREMENT,"
    "  `name` varchar(40),"
    "  `species` varchar(40),"
    "  PRIMARY KEY (`id`), UNIQUE KEY `id` (`id`)"
    ") ENGINE=InnoDB")

TABLES['temperature'] = (
    "CREATE TABLE if not exists `temperature` ("
    "  `id` int NOT NULL AUTO_INCREMENT,"
    "  `plant_id` int NOT NULL,"
    "  `temperature` int NOT NULL,"
    "  `created_on` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
    "  FOREIGN KEY (`plant_id`) REFERENCES `plants` (`id`) ON DELETE CASCADE,"
    "  PRIMARY KEY (`id`), UNIQUE KEY `id` (`id`)"
    ") ENGINE=InnoDB")

TABLES['humidity'] = (
    "CREATE TABLE if not exists `humidity` ("
    "  `id` int NOT NULL AUTO_INCREMENT,"
    "  `plant_id` int NOT NULL,"
    "  `humidity` int NOT NULL,"
    "  `created_on` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
    "  FOREIGN KEY (`plant_id`) REFERENCES `plants` (`id`) ON DELETE CASCADE,"
    "  PRIMARY KEY (`id`), UNIQUE KEY `id` (`id`)"
    ") ENGINE=InnoDB")

TABLES['sensors'] = (
    "CREATE TABLE `iot`.`sensors` ("
    " `id` INT NOT NULL AUTO_INCREMENT,"
    " `type` VARCHAR(45) NOT NULL,"
    " `plant_id` INT NOT NULL,"
    " PRIMARY KEY (`id`),"
    " FOREIGN KEY (`plant_id`) REFERENCES `plants` (`id`) ON DELETE CASCADE);"
    ") ENGINE=InnoDB")



cnx = mysql.connector.connect(**config)
cursor = cnx.cursor()
cursor.execute("USE iot")

for table_name in TABLES:
    table_description = TABLES[table_name]
    try:
        print("Creating table {}: ".format(table_name), end='')
        cursor.execute(table_description)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
            print("already exists.")
        else:
            print(err.msg)
    else:
        print("OK")

cursor.close()
cnx.close()

sensors = sensors.Sensors()
client = client.Client()