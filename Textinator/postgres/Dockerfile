FROM postgres:13.4-alpine

ENV SHAREDIR=/usr/local/share/postgresql

COPY tsearch_data/*.stop $SHAREDIR/tsearch_data/
COPY docker-entrypoint-initdb.d /docker-entrypoint-initdb.d
