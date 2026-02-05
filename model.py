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
from typing import Optional, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ModelSingleton:

    _instance: Optional['ModelSingleton'] = None
    _model: Optional[Pipeline] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelSingleton, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._model = self._load_model()

    def _train_model(self) -> Pipeline:
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

    def _save_model(self, model, path="model.pkl"):
        with open(path, "wb") as f:
            pickle.dump(model, f)

    def _register_model_in_mlflow(self):
        """Регистрирует модель в MLflow Model Registry"""
        try:
            
            mlflow.set_tracking_uri("sqlite:///mlflow.db")
            mlflow.set_experiment("moderation-model")
            
            with mlflow.start_run() as run:
                model = self._train_model()
                log_model(
                    model, 
                    name = "model", 
                    registered_model_name="moderation-model",
                    metadata={"suppress_pydantic_warnings": True}
                )
                
                client = MlflowClient()
                
                model_versions = client.search_model_versions(
                    f"name='moderation-model' and run_id='{run.info.run_id}'"
                )
                
                if model_versions:
                    latest_version = model_versions[0].version
                    client.set_registered_model_alias(
                        name="moderation-model",
                        alias="production",
                        version=latest_version
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

    def _load_model(self, path="model.pkl"):
        use_mlflow = os.getenv("USE_MLFLOW", "false").strip().lower() == "true"
        
        if use_mlflow:
            try:
                return self._load_model_from_mlflow()
            except Exception as e:
                logger.warning(f"MLflow loading failed, falling back to local file: {e}")
        try:
            with open(path, "rb") as f:
                model = pickle.load(f)
            logger.info("Model loaded successfully from file: %s", path)
            return model
        
        except FileNotFoundError:
            logger.info("Model not found at %s, training new model...", path)
            model = self._train_model()
            self._save_model(model)
            logger.info("Model trained and saved successfully to: %s", path)
            return model

    def _load_model_from_mlflow(self, model_name: str = "moderation-model", stage: str = "production"):
        try:
            model_uri = f"models:/{model_name}@{stage}"
            logger.info(f"Loading model from MLflow: {model_uri}")
            model = mlflow.sklearn.load_model(model_uri)
            logger.info("Model loaded successfully from MLflow")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model from MLflow: {e}")
            logger.info("Falling back to training new model...")
            model = self._train_model()
            self._save_model(model)
            logger.info("Model trained and saved successfully to: model.pkl")
            return model
    
    @property
    def is_loaded(self) -> bool:
        return self._model is not None

model_singleton = ModelSingleton()