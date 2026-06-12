import torch
import torch.nn as nn

class StandardTabularClassifier(nn.Module):
    """
    A standard feed-forward Multi-Layer Perceptron (MLP) Classifier.
    Used as the default target model for loading tabular PyTorch state dicts.
    """
    def __init__(self, input_dim: int = 2, hidden_dim: int = 4, output_dim: int = 2):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
            # Output raw logits; predictions will apply softmax
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)