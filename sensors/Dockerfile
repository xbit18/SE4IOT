FROM python:3.10
WORKDIR /app
COPY . .
RUN pip3 install paho-mqtt
RUN pip3 install numpy
RUN pip3 install requests
RUN pip3 install tenacity
CMD ["python3", "greenhouse.py"]