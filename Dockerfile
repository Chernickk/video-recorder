FROM python:3.9.5

COPY ./ ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN apt-get install ffmpeg

