FROM python:latest

MAINTAINER Jake Bunce github.com/jbunce

COPY server.py /server.py

COPY clusterhealthz_tests.py /clusterhealthz_tests.py

RUN mkdir /config/

COPY ./config/clusterhealthz.conf /config/clusterhealthz.conf

COPY ./favicon.ico /favicon.ico

RUN chmod +x /server.py

RUN chmod +x /clusterhealthz_tests.py

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["/server.py"]
