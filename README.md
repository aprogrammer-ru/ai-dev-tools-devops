# Distributed Counter Platform

## Компоненты

- `services/counter-api` — FastAPI сервис счетчика.
- `services/counter-api-dotnet` — .NET 8 Minimal API сервис счетчика.
- `infra/k8s` — Kubernetes манифесты.
- `infra/helm/observability` — конфигурации Logstash.
- `.github/workflows` — CI/CD для GitHub Actions.

## Быстрый старт (локально)

1. `docker compose up -d --build`
2. `curl http://localhost:8000/health/live` (Python)
3. `curl http://localhost:8080/health/live` (.NET)
