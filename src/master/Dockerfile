# FROM python:3.10-slim

# ENV PYTHONFAULTHANDLER=1
# ENV PYTHONUNBUFFERED=1
# ENV PYTHONHASHSEED=random
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PIP_NO_CACHE_DIR=off
# ENV PIP_DISABLE_PIP_VERSION_CHECK=on
# ENV PIP_DEFAULT_TIMEOUT=100
FROM debian:stable-slim

RUN apt-get update
RUN apt-get install -y python3 python3-pip python3-dev build-essential python3-venv ffmpeg

RUN mkdir -p /code /error /online

# Set up a virtual environment and activate it
RUN python3 -m venv /opt/venv

# Ensure commands run in the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

ADD ./requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN pip uninstall requests

ADD . /code
WORKDIR /code

CMD ["bash"]