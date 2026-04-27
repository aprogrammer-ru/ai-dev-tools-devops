Реализуй: "CI/CD и деплой в Yandex Cloud".

Ограничения:
- Не рефакторь API-логику, работай только с pipeline и деплоем.
- Используй GitHub Actions и Yandex Managed Kubernetes.

Сделай:
1. Настрой CI workflow:
   - lint
   - unit/integration tests
   - сборка docker image
   - базовый security scan.
2. Настрой публикацию образа в registry.
3. Настрой CD workflow:
   - деплой в Yandex Managed Kubernetes
   - rollout status/health check после выката.
4. Оформи работу с секретами через GitHub Secrets и Yandex IAM SA.

Критерий готовности:
- Push в основную ветку запускает полный pipeline и приводит к автоматическому деплою.
