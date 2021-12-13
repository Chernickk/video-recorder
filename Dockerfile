FROM ubuntu:hirsute


ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get -y update && apt-get -y install \
    python3 python3-pip ffmpeg iputils-ping
    
COPY ./ ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt



