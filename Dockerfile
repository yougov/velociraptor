FROM python:3.6

LABEL maintainer="Lorenzo Bolla <lorenzo.bolla@yougov.com>"

ADD . /app
WORKDIR /app

RUN pip install pip --upgrade
RUN pip install -e ./common
RUN pip install -e ./runners
RUN pip install -e ./builder
RUN pip install -e ./imager
RUN pip install -e ./server

CMD gunicorn --log-level debug -c gunicorn_config.py vr.server.wsgi:app
