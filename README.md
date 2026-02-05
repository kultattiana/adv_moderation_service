# Сервис модерации объявлений
HTTP API for simple web-service of ad moderation. 
HSE FCS Backend course project

## Инструкции по запуску

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Запуск сервера MLFlow
```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5002
```

### Создание БД внутри Docker
```
docker compose up -d
```

### Запуск сервера
```bash
uvicorn main:app --reload --port 8000
```

### Запуск тестов
```bash
pytest tests/
```
### Документация API
После запуска сервера доступна автоматическая документация Swagger UI: http://localhost:8000/docs

Интерфейс MLFlow: http://localhost:5002

### Пример ответа
```json
{
  "is_violation": false,
  "probability": 0.00000256
}
```
