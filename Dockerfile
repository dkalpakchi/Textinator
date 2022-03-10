# pull official base image
FROM python:3.9.6-alpine

# install psycopg2 dependencies and other dependencies
RUN apk update \
    && apk add build-base postgresql-dev gcc python3-dev musl-dev git jpeg-dev zlib-dev gettext libsass nodejs npm

RUN adduser -D tt
USER tt
WORKDIR /home/tt

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
RUN export PATH="$PATH:/home/tt/.local/bin"

RUN mkdir Textinator

COPY ./requirements.txt ./Textinator/
RUN pip install -r ./Textinator/requirements.txt

# copy project
# COPY . .

CMD ["export", 'PATH="$PATH:/home/tt/.local/bin"']

ENTRYPOINT sh /home/tt/Textinator/entrypoint.sh