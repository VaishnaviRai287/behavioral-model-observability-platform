import os
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
import torch
import torch.nn as nn

# Standard MLP matching standard loading structures
class StandardTabularClassifier(nn.Module):
    def __init__(self, input_dim: int = 2, hidden_dim: int = 4, output_dim: int = 2):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
    def forward(self, x):
        return self.network(x)

def main():
    artifacts_dir = os.path.abspath("model_artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    # 1. Train and save a simple Scikit-Learn Logistic Regression
    print("Generating Scikit-Learn Dummy Model...")
    X_train = np.array([[10, 50.0], [5, 20.0], [20, 80.0], [2, 15.0]])
    y_train = np.array([1, 0, 1, 0])
    
    sklearn_model = LogisticRegression()
    sklearn_model.fit(X_train, y_train)
    
    sklearn_path = os.path.join(artifacts_dir, "sklearn_logistic.joblib")
    joblib.dump(sklearn_model, sklearn_path)
    print(f"Saved Scikit-Learn Model to: {sklearn_path}")

    # 2. Save a simple PyTorch state dict matching StandardTabularClassifier
    print("Generating PyTorch Dummy Model weights...")
    torch_model = StandardTabularClassifier(input_dim=2, hidden_dim=4, output_dim=2)
    # Set default weights to avoid non-deterministic test asserts
    for layer in torch_model.network:
        if isinstance(layer, nn.Linear):
            nn.init.constant_(layer.weight, 0.5)
            nn.init.constant_(layer.bias, 0.0)
            
    torch_path = os.path.join(artifacts_dir, "pytorch_mlp.pt")
    torch.save(torch_model.state_dict(), torch_path)
    print(f"Saved PyTorch State Dict to: {torch_path}")

if __name__ == "__main__":
    main()