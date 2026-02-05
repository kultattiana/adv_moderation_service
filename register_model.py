import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from model import model_singleton
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Registering model in MLflow...")
    logger.info("Model registered successfully!")