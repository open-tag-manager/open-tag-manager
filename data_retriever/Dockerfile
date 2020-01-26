FROM python:3.6.5-alpine
WORKDIR /usr/src/app
RUN apk --update-cache \
    add musl \
    linux-headers \
    gcc \
    g++ \
    make \
    gfortran \
    openblas-dev \
    python3 \
    python3-dev
ENV PYTHONPATH /usr/src/app
COPY requirements.txt /usr/src/app
RUN pip3 install --upgrade pip
RUN pip3 install numpy
RUN pip3 install -r requirements.txt
COPY ./ /usr/src/app
