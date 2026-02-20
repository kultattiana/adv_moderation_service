import sys
sys.path.append('.')
from typing import Any, Mapping, Generator
import pytest
from fastapi.testclient import TestClient
from http import HTTPStatus
import os
import uuid
from fastapi import FastAPI, HTTPException
from unittest.mock import AsyncMock, patch
from routers import predict
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from clients.postgres import get_pg_connection
from clients.redis import get_redis_connection
from repositories.ads import AdRepository
from datetime import datetime
from repositories.sellers import SellerRepository
from contextlib import asynccontextmanager
from services.sellers import SellerService
from routers import health, async_predict, ads, sellers, moderation_results, predict
from typing import AsyncIterator

from workers.moderation_worker import KafkaConsumerWorker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(
    title = 'Ad Moderation Service',
    description = 'Сервис модерации объявлений',
    version = '1.0.0',
    lifespan = lifespan
)

app.include_router(health.router)
app.include_router(async_predict.router)
app.include_router(predict.router)
app.include_router(ads.router, prefix='/ads')
app.include_router(sellers.router, prefix='/sellers')
app.include_router(sellers.root_router)
app.include_router(moderation_results.router, prefix = '/moderation_results')

@pytest.fixture
def app_client() -> Generator[TestClient, None, None]:
    return TestClient(app)


@pytest.fixture
def valid_ad_data():
    return {
        "seller_id": 123,
        "is_verified_seller": True,
        "item_id": 456,
        "name": "Test Product",
        "description": "Test Description",
        "category": 5,
        "images_qty": 3
    }

@pytest.fixture
def seller_data() -> Mapping[str, Any]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'username': f'Иванов В.П. {unique_id}',
        'email': f'ivanovvp_{unique_id}@mail.ru',
        'password': f'password123_{unique_id}'
    }

@pytest.fixture
def item_data() -> Mapping[str, Any]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'name': f'Товар 1 {unique_id}',
        'description': f'Стандартный',
        'category': 0,
        'images_qty': 5
    }

@pytest.fixture
def item_zero_images() -> Mapping[str, Any]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'name': f'Товар 2 {unique_id}',
        'description': f'Стандартный',
        'category': 0,
        'images_qty': 0
    }

@pytest.fixture
def created_seller(app_client: TestClient, seller_data: Mapping[str, Any]):
    response = app_client.post('/sellers/', json=seller_data)
    assert response.status_code == HTTPStatus.CREATED
    seller = response.json()
    yield seller
    app_client.delete(
        f'/sellers/{seller["seller_id"]}',
        cookies={'x-user-id': str(seller['seller_id'])}

    )

@pytest.fixture
def logged_seller(app_client: TestClient, created_seller: dict) -> dict:

    login_data = {
            'email': created_seller['email'],
            'password': created_seller['password']
        }
        
    response = app_client.post('/login', json=login_data)
    assert response.status_code == HTTPStatus.OK
    return created_seller

@pytest.fixture
def created_seller_data(seller_data):
    return {
        'seller_id': 1,
        **seller_data,
        'is_verified': False
    }

@pytest.fixture
def logged_seller_data(created_seller_data):
    return created_seller_data


@pytest.fixture
def verified_seller(app_client: TestClient, logged_seller: dict) -> dict:
    app_client.patch(
        f'/sellers/verify/{logged_seller["seller_id"]}',
        cookies={'x-user-id': str(logged_seller['seller_id'])}
    )
    return logged_seller

@pytest.fixture
def verified_seller_data(seller_data):
    return {
        'seller_id': 1,
        **seller_data,
        'is_verified': True
    }


@pytest.fixture
def created_task_data():
    """Мок данные задачи модерации для юнит-тестов"""
    return {
        'task_id': 1,
        'item_id': 1,
        'status': 'pending',
        'is_violation': None,
        'probability': None
    }

@pytest.fixture
def created_moderation(created_task_data, created_item_data):
    return {
            "id": created_task_data["task_id"],
            "item_id": created_item_data['item_id'],
            "status": "pending",
            "is_violation": None,
            "probability": None,
            "error_message": None,
            "created_at": datetime.now().isoformat(),
            "processed_at": None
        }

@pytest.fixture
def completed_moderation(created_task_data, created_item_data):
    return {
            "id": created_task_data["task_id"],
            "item_id": created_item_data['item_id'],
            "status": "completed",
            "is_violation": False,
            "probability": 0.0,
            "error_message": None,
            "created_at": datetime.now().isoformat(),
            "processed_at": datetime.now().isoformat()
        }

@pytest.fixture
def pending_moderation(created_task_data, created_item_data):
    return {
        "id": created_task_data["task_id"],
        "item_id": created_item_data['item_id'],
        "status": "pending",
        "is_violation": None,
        "probability": None,
        "error_message": None,
        "created_at": datetime.now().isoformat(),
        "processed_at": None
    }

@pytest.fixture
def created_item(app_client: TestClient, item_data: Mapping[str, Any], logged_seller: Mapping[str, any]):
    response = app_client.post('/ads/', json=item_data)
    assert response.status_code == HTTPStatus.CREATED
    item = response.json()
    yield item
    app_client.delete(
        f'/ads/{item["item_id"]}',
        cookies={'x-user-id': str(logged_seller['seller_id'])}
    )

@pytest.fixture
def created_item_data() -> Mapping[str, Any]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'item_id': 1,
        'name': f'Товар 1 {unique_id}',
        'seller_id': 1,
        'description': f'Стандартный',
        'category': 0,
        'images_qty': 5,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

@pytest.fixture
def created_item_zero_images(app_client: TestClient, item_zero_images: Mapping[str, Any], logged_seller: Mapping[str, any]):
    response = app_client.post('/ads/', json=item_zero_images)
    assert response.status_code == HTTPStatus.CREATED
    item = response.json()
    yield item
    app_client.delete(
        f'/ads/{item["item_id"]}',
        cookies={'x-user-id': str(logged_seller['seller_id'])}
    )

@pytest.fixture
def created_item_zero_images_data() -> Mapping[str, Any]:
    unique_id = str(uuid.uuid4())[:8]
    return {
        'item_id': 1,
        'name': f'Товар 1 {unique_id}',
        'seller_id': 1,
        'description': f'Стандартный',
        'category': 0,
        'images_qty': 0,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

@pytest.fixture
def created_task_pending(app_client, created_item):
    mock_producer = AsyncMock()
    mock_producer.send_moderation_request = AsyncMock()
    mock_producer.send_moderation_request.return_value = True
    
    with patch('routers.async_predict.kafka_producer', mock_producer):
        response = app_client.get(f'/ads/{created_item["item_id"]}')
        assert response.status_code == HTTPStatus.OK
        item_id = created_item["item_id"]
        
        response = app_client.post(
            f"/async_predict/{item_id}",
            json={"item_id": item_id}
        )

        task_data = response.json()
        task_id = task_data["task_id"]
        
        yield task_data

        app_client.delete(
            f'/moderation_results/{task_id}'
        )

@pytest.fixture
def worker():
    worker = KafkaConsumerWorker()
    worker.mod_service = AsyncMock()
    worker.ml_service = AsyncMock()
    worker.consumer = AsyncMock(spec=AIOKafkaConsumer)
    worker.dlq_producer = AsyncMock(spec=AIOKafkaProducer)
    
    return worker
    
@pytest.fixture
def sample_message(created_item, created_task_pending):
    return {
        "task_id": created_task_pending["task_id"],
        "item_id": created_item["item_id"],
        "timestamp": "2026-02-11T22:15:07.276334+00:00",
        "event_type": "moderation_request",
        "metadata": {
            "source": "advertisement_service",
            "version": "1.0"
        }
    }

@pytest.fixture
def sample_message_data(created_item_data, created_task_data):
    return {
        "task_id": created_task_data["task_id"],
        "item_id": created_item_data["item_id"],
        "timestamp": "2026-02-11T22:15:07.276334+00:00",
        "event_type": "moderation_request",
        "metadata": {
            "source": "advertisement_service",
            "version": "1.0"
        }
    }

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    return redis

@pytest.fixture
def mock_ad_service(mock_db_session):
    repo = AsyncMock(spec=AdRepository)
    repo.get_by_item_id = AsyncMock()
    repo.get_many = AsyncMock()
    repo.get_by_seller_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    repo.close = AsyncMock()
    repo.get_for_simple_predict = AsyncMock()
    return repo

@pytest.fixture
def mock_ad_storage():
    storage = AsyncMock()
    storage.create = AsyncMock()
    storage.get_by_item_id = AsyncMock()
    storage.get_many = AsyncMock()
    storage.get_by_seller_id = AsyncMock()
    storage.update = AsyncMock()
    storage.delete = AsyncMock()
    return storage

@pytest.fixture
def mock_seller_storage():
    storage = AsyncMock()
    storage.select_by_seller_id = AsyncMock()
    storage.create = AsyncMock()
    storage.update = AsyncMock()
    storage.delete = AsyncMock()
    return storage

@pytest.fixture
def mock_seller_service():
    mock_seller_repo = SellerRepository(seller_storage=mock_seller_storage, moderation_repo=AsyncMock())
    mock_seller_service = SellerService(seller_repo=mock_seller_repo)
    return mock_seller_service


@pytest.fixture
def app_client_with_mocks(mock_db_session, mock_redis):
    
    async def override_get_db():
        yield mock_db_session
    
    async def override_get_redis():
        yield mock_redis
    
    app.dependency_overrides[get_pg_connection] = override_get_db
    app.dependency_overrides[get_redis_connection] = override_get_redis
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()