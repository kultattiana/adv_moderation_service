import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import pickle
import logging
import mlflow
from mlflow.sklearn import log_model
import os
import warnings
from mlflow.tracking import MlflowClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def train_model() -> Pipeline:
    """Обучает простую модель на синтетических данных."""
    np.random.seed(42)
    # Признаки: [is_verified_seller, images_qty, description_length, category]
    X = np.random.rand(1000, 4)
    # Целевая переменная: 1 = нарушение, 0 = нет нарушения
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)

    model = Pipeline(
        [
            ("clf", LogisticRegression()),
        ]
    )
    model.fit(X, y)
    return model

def save_model(model, path="model.pkl"):
    with open(path, "wb") as f:
        pickle.dump(model, f)

def register_model_in_mlflow():
    """Регистрирует модель в MLflow Model Registry"""
    try:
        
        # Настройка MLflow
        mlflow.set_tracking_uri("sqlite:///mlflow.db")
        mlflow.set_experiment("moderation-model")
        
        with mlflow.start_run() as run:
            # Обучаем модель
            model = train_model()
            # Регистрируем модель
            log_model(
                model, 
                "model", 
                registered_model_name="moderation-model",
                metadata={"suppress_pydantic_warnings": True}
            )
            
            client = MlflowClient()
            
            # Находим последнюю версию модели
            model_versions = client.search_model_versions(
                f"name='moderation-model' and run_id='{run.info.run_id}'"
            )
            
            if model_versions:
                # Переводим модель на стадию Production
                latest_version = model_versions[0].version
                client.transition_model_version_stage(
                    name="moderation-model",
                    version=latest_version,
                    stage="Production"
                )
                
                logger.info(f"Model registered in MLflow successfully (version {latest_version}, stage: Production)")
            else:
                logger.warning("Model was logged but no version found")

            return model
            
    except ImportError:
        logger.error("MLflow is not installed. Please install it: pip install mlflow")
        raise
    except Exception as e:
        logger.error(f"Failed to register model in MLflow: {e}")
        raise

def load_model(path="model.pkl"):
    use_mlflow = os.getenv("USE_MLFLOW", "false").strip().lower() == "true"
    
    if use_mlflow:
        try:
            return load_model_from_mlflow()
        except Exception as e:
            logger.warning(f"MLflow loading failed, falling back to local file: {e}")
    try:
        with open(path, "rb") as f:
            model = pickle.load(f)
        logger.info("Model loaded successfully from file: %s", path)
        return model
    
    except FileNotFoundError:
        logger.info("Model not found at %s, training new model...", path)
        model = train_model()
        save_model(model)
        logger.info("Model trained and saved successfully to: %s", path)
        return model

def load_model_from_mlflow(model_name: str = "moderation-model", stage: str = "Production"):
    """Загружает модель из MLflow Model Registry"""
    try:
        
        model_uri = f"models:/{model_name}/{stage}"
        logger.info(f"Loading model from MLflow: {model_uri}")
        model = mlflow.sklearn.load_model(model_uri)
        logger.info("Model loaded successfully from MLflow")
        return model
        
    except Exception as e:
        logger.error(f"Failed to load model from MLflow: {e}")
        logger.info("Falling back to training new model...")
        model = train_model()
        save_model(model)
        logger.info("Model trained and saved successfully to: model.pkl")
        return model
