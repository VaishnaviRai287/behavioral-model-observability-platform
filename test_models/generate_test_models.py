#!/usr/bin/env python3
"""
Generates the test model artifacts in this directory.

The previous versions of these files were opaque binary pickles with no
source: a LogisticRegression fit on 4 hand-picked points (sklearn) and an
untrained nn.Sequential (pytorch), so they carried no real decision boundary
and there was no TensorFlow artifact at all. This script replaces them with
models trained on a synthetic-but-coherent churn dataset, across all three
frameworks ModelMesh ingests, with real held-out accuracy.

Usage (sklearn + PyTorch run anywhere):
    .venv/bin/python test_models/generate_test_models.py

TensorFlow requires the Python 3.10 environment used by the Docker image
(numpy<2.0 / tensorflow<2.17 constraint — see requirements.txt):
    docker compose run --rm api python test_models/generate_test_models.py
"""
import json
import pickle
from pathlib import Path

import numpy as np

SEED = 42
N_SAMPLES = 2000
OUTPUT_DIR = Path(__file__).parent

SCHEMA = {
    "features": [
        {"name": "tenure", "type": "float", "min": 0.0, "max": 100.0},
        {"name": "monthly_charges", "type": "float", "min": 0.0, "max": 200.0},
        {"name": "total_charges", "type": "float", "min": 0.0, "max": 20000.0},
    ]
}


def make_churn_dataset(n: int = N_SAMPLES, seed: int = SEED):
    """
    Churn risk rises with monthly_charges and falls with tenure, with a mild
    total_charges effect and Gaussian noise on top — every model trained on
    this has a real, learnable boundary instead of fitting a handful of
    arbitrary points.
    """
    rng = np.random.default_rng(seed)
    tenure = rng.uniform(0, 72, n)
    monthly_charges = rng.uniform(20, 150, n)
    total_charges = tenure * monthly_charges * rng.uniform(0.85, 1.15, n)

    logit = (
        -0.05 * tenure
        + 0.04 * monthly_charges
        - 0.00005 * total_charges
        + rng.normal(0, 0.75, n)
    )
    churn = (logit > np.median(logit)).astype(np.int64)  # balanced classes

    X = np.column_stack([tenure, monthly_charges, total_charges]).astype(np.float32)
    return X, churn


def split(X, y, test_frac: float = 0.2, seed: int = SEED):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(X))
    cut = int(len(X) * (1 - test_frac))
    train_idx, test_idx = idx[:cut], idx[cut:]
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


def build_sklearn_model(X_train, y_train, X_test, y_test) -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    print(f"  sklearn     LogisticRegression + StandardScaler   test accuracy = {acc:.3f}")

    path = OUTPUT_DIR / "churn_sklearn_model.pkl"
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"              saved -> {path.name}")


def build_pytorch_model(X_train, y_train, X_test, y_test) -> None:
    import torch
    import torch.nn as nn

    torch.manual_seed(SEED)

    # total_charges spans 0-10,000+ while tenure spans 0-72 — without
    # standardizing, that one feature dominates the gradient and the model
    # underfits everything else. PyTorchWrapper does `torch.load(path)` on a
    # *full* pickled object, in a process that only has `torch.nn` itself
    # importable — a custom nn.Module subclass defined in this script would
    # fail to unpickle there. So the scaler has to be expressed as a frozen
    # nn.Linear (a diagonal affine map), keeping the whole model built from
    # stock torch.nn layers.
    mean = torch.tensor(X_train.mean(axis=0), dtype=torch.float32)
    std = torch.tensor(X_train.std(axis=0), dtype=torch.float32)

    scaler = nn.Linear(3, 3)
    with torch.no_grad():
        scaler.weight.copy_(torch.diag(1.0 / std))
        scaler.bias.copy_(-mean / std)
    scaler.weight.requires_grad_(False)
    scaler.bias.requires_grad_(False)

    model = nn.Sequential(
        scaler,
        nn.Linear(3, 8),
        nn.ReLU(),
        nn.Linear(8, 2),
    )
    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable, lr=0.01)
    loss_fn = nn.CrossEntropyLoss()

    Xt = torch.tensor(X_train, dtype=torch.float32)
    yt = torch.tensor(y_train, dtype=torch.long)

    model.train()
    for _ in range(200):
        opt.zero_grad()
        loss = loss_fn(model(Xt), yt)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        preds = model(torch.tensor(X_test, dtype=torch.float32)).argmax(dim=1).numpy()
    acc = (preds == y_test).mean()
    print(f"  pytorch     scaler→3→8→2 MLP, 200 epochs Adam     test accuracy = {acc:.3f}")

    path = OUTPUT_DIR / "churn_pytorch_model.pt"
    torch.save(model, path)  # full object, not a state_dict — required by PyTorchWrapper
    print(f"              saved -> {path.name}")


def build_tensorflow_model(X_train, y_train, X_test, y_test) -> None:
    try:
        import tensorflow as tf
    except ImportError:
        print("  tensorflow  SKIPPED — not installed in this environment.")
        print("              run inside the Docker image instead:")
        print("              docker compose run --rm api python test_models/generate_test_models.py")
        return

    tf.random.set_seed(SEED)

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(3,)),
        tf.keras.layers.Dense(8, activation="relu"),
        tf.keras.layers.Dense(2, activation="softmax"),
    ])
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(X_train, y_train, epochs=30, verbose=0)

    _, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"  tensorflow  3→8→2 Keras Sequential, 30 epochs     test accuracy = {acc:.3f}")

    path = OUTPUT_DIR / "churn_tensorflow_model.keras"
    model.save(path)
    print(f"              saved -> {path.name}")


def main() -> None:
    print(f"Generating churn test models (seed={SEED}, n={N_SAMPLES})\n")
    X, y = make_churn_dataset()
    X_train, X_test, y_train, y_test = split(X, y)
    print(f"  churn rate: {y.mean():.2f}   train={len(X_train)}   test={len(X_test)}\n")

    build_sklearn_model(X_train, y_train, X_test, y_test)
    build_pytorch_model(X_train, y_train, X_test, y_test)
    build_tensorflow_model(X_train, y_train, X_test, y_test)

    schema_path = OUTPUT_DIR / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA, indent=2) + "\n")
    print(f"\n  schema      -> {schema_path.name}")
    print("\nUpload any of these to POST /api/v1/models with schema.json as the schema field.")


if __name__ == "__main__":
    main()
