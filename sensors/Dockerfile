FROM python:3.10
WORKDIR /app
COPY . .
RUN pip3 install paho-mqtt
RUN pip3 install numpy
CMD ["python3", "greenhouse.py"]