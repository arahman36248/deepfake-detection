import torch
import cv2
import numpy as np
from pathlib import Path
from deepfake_model.model_utils import create_model

class DeepfakeDetector:
    def __init__(self, model_path, device='cpu'):
        self.device = torch.device(device)
        self.model = self._load_model(model_path)
        self.model.eval()

    def _load_model(self, model_path):
        model = create_model('simple', self.device)
        if Path(model_path).exists():
            state_dict = torch.load(model_path, map_location=self.device)
            model.load_state_dict(state_dict)
        return model

    def preprocess_image(self, image_path):
        """
        Preprocess image with proper ImageNet normalization
        """
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize
        image = cv2.resize(image, (224, 224))
        
        # Convert to float and normalize to [0, 1]
        image = image.astype(np.float32) / 255.0
        
        # Apply ImageNet normalization (CRITICAL FIX!)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        image = (image - mean) / std
        
        # Convert to tensor
        image = torch.from_numpy(image).float()
        image = image.permute(2, 0, 1).unsqueeze(0)
        
        return image.to(self.device)

    def analyze_file(self, file_path):
        file_ext = Path(file_path).suffix.lower()
        if file_ext in ['.mp4', '.avi', '.mov', '.mkv']:
            return self._analyze_video(file_path)
        else:
            return self._analyze_image(file_path)

    def _analyze_image(self, image_path):
        image = self.preprocess_image(image_path)
        with torch.no_grad():
            output = self.model(image)
        confidence = output.item()
        prediction = "FAKE" if confidence > 0.5 else "REAL"
        return {
            'prediction': prediction,
            'confidence': confidence,
            'details': {'method': 'single_frame_analysis', 'model': 'ResNet18'}
        }

    def _analyze_video(self, video_path, sample_frames=10):
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_indices = np.linspace(0, total_frames-1, sample_frames, dtype=int)
        predictions = []
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (224, 224))
                frame = frame.astype(np.float32) / 255.0
                
                # Apply ImageNet normalization
                mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
                std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
                frame = (frame - mean) / std
                
                frame = torch.from_numpy(frame).float()
                frame = frame.permute(2, 0, 1).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    output = self.model(frame)
                predictions.append(output.item())
        cap.release()
        avg_confidence = np.mean(predictions)
        prediction = "FAKE" if avg_confidence > 0.5 else "REAL"
        return {
            'prediction': prediction,
            'confidence': avg_confidence,
            'details': {
                'method': 'video_sampling',
                'frames_analyzed': len(predictions),
                'total_frames': total_frames
            }
        }
