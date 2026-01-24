import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import pickle
import logging

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

def load_model(path="model.pkl"):
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

