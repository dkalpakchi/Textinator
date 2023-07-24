CREATE TEXT SEARCH DICTIONARY public.english_lite (
   TEMPLATE = pg_catalog.simple,
   STOPWORDS = english_lite
);

CREATE TEXT SEARCH CONFIGURATION public.english_lite (
   COPY = pg_catalog.english
);

ALTER TEXT SEARCH CONFIGURATION public.english_lite
   ALTER MAPPING
      FOR asciiword, asciihword, hword_asciipart, hword, hword_part, word
      WITH english_lite;

CREATE TEXT SEARCH DICTIONARY public.ukrainian_huns (
  TEMPLATE = ispell, DictFile = uk_UA, AffFile = uk_UA, StopWords = ukrainian
);

CREATE TEXT SEARCH DICTIONARY public.ukrainian_stem (
  template = simple, stopwords = ukrainian
);

CREATE TEXT SEARCH CONFIGURATION public.ukrainian (
  PARSER=default
);

ALTER TEXT SEARCH CONFIGURATION public.ukrainian
  ALTER MAPPING 
    FOR hword, hword_part, word
    WITH ukrainian_huns, ukrainian_stem;

ALTER TEXT SEARCH CONFIGURATION public.ukrainian
  ALTER MAPPING
    FOR int, uint, numhword, numword, hword_numpart, email, float, file, url, url_path, version, host, sfloat
    WITH simple;

ALTER TEXT SEARCH CONFIGURATION public.ukrainian
  ALTER MAPPING 
    FOR asciihword, asciiword, hword_asciipart 
    WITH english_stem;

CREATE TEXT SEARCH DICTIONARY public.ukrainian_huns_lite (
  TEMPLATE = ispell, DictFile = uk_UA, AffFile = uk_UA, StopWords = ukrainian_lite
);

CREATE TEXT SEARCH DICTIONARY public.ukrainian_stem_lite (
  template = simple, stopwords = ukrainian_lite
);

CREATE TEXT SEARCH CONFIGURATION public.ukrainian_lite (
  PARSER=default
);

ALTER TEXT SEARCH CONFIGURATION public.ukrainian_lite
  ALTER MAPPING 
    FOR hword, hword_part, word
    WITH ukrainian_huns_lite, ukrainian_stem_lite;

ALTER TEXT SEARCH CONFIGURATION public.ukrainian_lite
  ALTER MAPPING
    FOR int, uint, numhword, numword, hword_numpart, email, float, file, url, url_path, version, host, sfloat
    WITH simple;

ALTER TEXT SEARCH CONFIGURATION public.ukrainian_lite
  ALTER MAPPING 
    FOR asciihword, asciiword, hword_asciipart 
    WITH english_stem;
