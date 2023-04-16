From python:3.10-alpine

Run apk add --no-cache python3-dev \
    && pip3 install --upgrade pip

Workdir /app

ENV FLASK_APP=app.py

ENV FLASK_RUN_HOST 0.0.0.0

Run apk add --no-cache gcc musl-dev linux-headers

Copy requirements.txt requirements.txt

Run pip install -r requirements.txt

Copy . .

CMD [ "flask" , "run" ]