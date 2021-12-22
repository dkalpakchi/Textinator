# pull official base image
FROM python:3.9.6-alpine

# install psycopg2 dependencies and other dependencies
RUN apk update \
    && apk add build-base postgresql-dev gcc python3-dev musl-dev git jpeg-dev zlib-dev gettext libsass

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
COPY ./django_scientific_survey-0.1-py3-none-any.whl .
RUN pip install -r requirements.txt

# copy project
# COPY . .

CMD ["export", 'PATH="$PATH:/home/textinator/.local/bin"']