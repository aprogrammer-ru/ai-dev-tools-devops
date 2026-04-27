#!/bin/bash

# Запуск postgres и redis (базовые зависимости)
docker compose up -d postgres redis

# Даем немного времени на инициализацию баз данных
sleep 5

# Запуск logstash (не зависит от других сервисов)
docker compose up -d logstash

# Запуск loki и grafana (после логирования)
# Loki доступен по адресу: http://localhost:3100
# Grafana доступна по адресу: http://localhost:3000 (admin/admin)
docker compose up -d loki grafana

# Запуск counter-api-dotnet (автоматически подождёт postgres и redis)
# Swagger доступен по адресу: http://localhost:5080/swagger
docker compose up -d counter-api-dotnet
