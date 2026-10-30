FROM mysql:8.4

COPY SQL/schema.sql /docker-entrypoint-initdb.d/01-schema.sql

CMD ["mysqld", "--innodb-buffer-pool-size=64M", "--performance-schema=OFF"]
