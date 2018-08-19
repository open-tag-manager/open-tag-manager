FROM python:3.6.5-alpine
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app
RUN pip install -r requirements.txt

COPY app.py /usr/src/app
ENTRYPOINT ["python", "app.py"]
