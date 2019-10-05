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
COPY requirements.txt /usr/src/app
RUN pip3 install --upgrade pip
RUN pip3 install numpy
RUN pip3 install -r requirements.txt

COPY app.py /usr/src/app
COPY goals.py /usr/src/app
COPY retriever_base.py /usr/src/app
ENTRYPOINT ["python", "app.py"]
