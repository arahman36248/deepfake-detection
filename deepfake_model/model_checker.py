"""
Model calibration and health check
"""
import torch
import numpy as np
from pathlib import Path

def check_model_training_status(model_path):
    """
    Check if model has been trained on deepfakes
    
    Returns:
        dict with training status and recommendations
    """
    model_path = Path(model_path)
    
    # Check if custom trained model exists
    if not model_path.exists():
        return {
            'trained': False,
            'status': 'Using ImageNet pre-trained weights',
            'accuracy_estimate': '60-70% (random baseline)',
            'recommendation': 'Train on deepfake dataset for 80%+ accuracy'
        }
    
    # Check file size (trained models are usually different size)
    file_size_mb = model_path.stat().st_size / (1024 * 1024)
    
    if 44 < file_size_mb < 47:  # Standard ResNet18 size
        return {
            'trained': False,
            'status': 'Using pre-trained ResNet18',
            'accuracy_estimate': '65-75% baseline',
            'recommendation': 'Fine-tune on FaceForensics++ or CelebDF'
        }
    else:
        return {
            'trained': True,
            'status': 'Custom trained model detected',
            'accuracy_estimate': 'Depends on training data',
            'recommendation': 'Monitor validation accuracy'
        }

def calibrate_threshold(validation_outputs, validation_labels):
    """
    Find optimal threshold from validation data
    
    Args:
        validation_outputs: Model predictions (0-1)
        validation_labels: True labels (0=real, 1=fake)
    
    Returns:
        Optimal threshold value
    """
    thresholds = np.linspace(0.3, 0.7, 100)
    best_accuracy = 0
    best_threshold = 0.5
    
    for thresh in thresholds:
        predictions = (validation_outputs > thresh).astype(int)
        accuracy = (predictions == validation_labels).mean()
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = thresh
    
    return best_threshold, best_accuracy

# For immediate use: print model status
if __name__ == '__main__':
    status = check_model_training_status('models/trained_model.pth')
    print("Model Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
