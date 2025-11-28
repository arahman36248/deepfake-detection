import unittest
import torch
from deepfake_model.model_utils import create_model

class TestDeepfakeDetector(unittest.TestCase):
    def test_model_creation_simple(self):
        model = create_model('simple', 'cpu')
        self.assertIsNotNone(model)
        dummy_input = torch.randn(1, 3, 224, 224)
        output = model(dummy_input)
        self.assertEqual(output.shape, torch.Size([1, 1]))
        self.assertTrue(0 <= output.item() <= 1)

    # Add more tests as needed

if __name__ == '__main__':
    unittest.main()
