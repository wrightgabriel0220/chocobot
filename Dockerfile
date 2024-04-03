FROM python:3.11.8-bookworm

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY music.py ./
COPY guild_archive.example.json ./guild_archive.json

CMD [ "python", "-u", "./main.py" ]