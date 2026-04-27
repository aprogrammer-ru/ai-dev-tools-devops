```mermaid
flowchart TD
    Start([GitHub Event]) --> Trigger{{"push на main / pull_request"}}
    Trigger --> Checkout["Checkout код"]
    Checkout --> PythonSetup["Python 3.12"]
    PythonSetup --> Install["pip install -e .[dev]"]
    Install --> Lint["ruff check"]
    Lint --> Test["pytest"]
    Test --> Build["Mock build"]
    Build --> Finish([Успешно])

    style Start fill:#f9f,stroke:#333
    style Finish fill:#9f9,stroke:#333
    style Trigger fill:#ccf,stroke:#333
```

**Легенда шагов:**

| Шаг | Описание |
|-----|---------|
| **Checkout код** | Загрузка исходного кода из репозитория |
| **Python 3.12** | Установка Python 3.12 |
| **pip install** | Установка dev-зависимостей |
| **ruff check** | Проверка стиля кода |
| **pytest** | Запуск тестов |
| **Mock build** | Имитация сборки |

**Логика запуска:**

- `build` → запуск при любом `push`
- `test` → запуск только при `push` на `main`, требует успешного `build`