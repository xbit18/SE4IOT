FROM python:3.10
WORKDIR /app
COPY . .
RUN pip3 install paho-mqtt
RUN pip3 install Flask
RUN pip3 install requests
CMD ["python3", "config.py"]