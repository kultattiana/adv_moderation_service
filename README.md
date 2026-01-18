# Сервис модерации объявлений
HTTP API for simple web-service of ad moderation. 
HSE FCS Backend course project

# ДЗ1
## Инструкции по запуску

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Запуск сервера
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Запуск тестов
```bash
pytest tests/test_api.py
```
### Документация API
После запуска сервера доступна автоматическая документация Swagger UI: http://localhost:8000/docs

### Пример ответа
```json
{
  "is_approved": true,
  "message": "Неверифицированный продавец, есть изображения"
}
```"# adv_moderation_service" 
