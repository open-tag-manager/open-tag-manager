FROM python:3.6-buster
WORKDIR /usr/src/app
ENV PYTHONPATH /usr/src/app
COPY requirements.txt /usr/src/app
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
COPY ./ /usr/src/app
