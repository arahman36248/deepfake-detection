"""Deepfake detection model package"""

from deepfake_model.detector import DeepfakeDetector
from deepfake_model.model_utils import create_model

__all__ = ['DeepfakeDetector', 'create_model']
