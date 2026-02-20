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
```bash
docker compose up -d
```

### Запуск Kafka Consumer (необходимо запустить до запуска сервера, модель подгружается на стороне консьюмера)
```bash
python -m workers.moderation_worker
```

### Запуск сервера
```bash
uvicorn main:app --reload --port 8000
```

### Запуск всех тестов
```bash
pytest tests/
```

### Запуск только интеграционных тестов
```bash
pytest -m integration
```

### Запуск только юнит-тестов (работают без поднятия хранилища и кафки)
```bash
pytest -m "not integration"
```

### Документация API
После запуска сервера доступна автоматическая документация Swagger UI: http://localhost:8000/docs

Интерфейс MLFlow: http://localhost:5002

Интерфейс Kafka: http://localhost:8080

### Пример ответа
```json
{
  "is_violation": false,
  "probability": 0.00000256
}
```
