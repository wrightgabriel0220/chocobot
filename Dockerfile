FROM python:3.11.8-bookworm

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY music.py ./
COPY .env ./
COPY application.yml ./

CMD [ "python", "./main.py" ]