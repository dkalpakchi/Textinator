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
