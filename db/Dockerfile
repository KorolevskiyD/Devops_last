FROM postgres:15

COPY init_db.sql .
#RUN apt-get update && apt-get install -y gosu && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y su-exec && rm -rf /var/lib/apt/lists/*



EXPOSE 5432
