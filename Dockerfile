# pull official base image
FROM python:3.9.6-alpine

RUN apk add git

RUN adduser -D textinator
USER textinator
WORKDIR /home/textinator

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
RUN export PATH="$PATH:/home/textinator/.local/bin"

COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .