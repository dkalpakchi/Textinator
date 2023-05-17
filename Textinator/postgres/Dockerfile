FROM postgres:13.4-alpine

ENV SHAREDIR=/usr/local/share/postgresql

COPY tsearch_data/*.stop $SHAREDIR/tsearch_data/
COPY tsearch_data/uk_UA.aff $SHAREDIR/tsearch_data/uk_ua.affix
COPY tsearch_data/uk_UA.dic $SHAREDIR/tsearch_data/uk_ua.dict
COPY docker-entrypoint-initdb.d /docker-entrypoint-initdb.d
