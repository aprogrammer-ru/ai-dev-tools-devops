# Counter API .NET

Minimal API на .NET 8 для распределенного счетчика.

## Endpoint'ы

- `GET /health/live`
- `GET /health/ready`
- `GET /v1/counters/{counterKey}`
- `POST /v1/counters/{counterKey}/increment` (`Idempotency-Key` поддерживается)
