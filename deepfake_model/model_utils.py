import torch
import torch.nn as nn
import torchvision.models as models

class SimpleResNetDeepfakeDetector(nn.Module):
    def __init__(self, pretrained=True):
        super(SimpleResNetDeepfakeDetector, self).__init__()
        self.resnet = models.resnet18(pretrained=pretrained)
        self.resnet.fc = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )
    def forward(self, x):
        return self.resnet(x)

def create_model(model_type='simple', device='cpu'):
    if model_type == 'simple':
        model = SimpleResNetDeepfakeDetector(pretrained=True)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    return model.to(device)
