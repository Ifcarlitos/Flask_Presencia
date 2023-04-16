From python:3.10-alpine

Workdir /app


ENV FLASK_APP=app.py

ENV FLASK_RUN_HOST 0.0.0.0

Run apk add --no-cache gcc musl-dev linux-headers

Copy requirements.txt requirements.txt

Run pip install --upgrade pip

Run pip install -r requirements.txt

Copy . .

CMD [ "flask" , "run" ]