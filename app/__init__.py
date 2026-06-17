import os

# Fix OpenMP multithreading runtime conflict crashes on macOS (Apple Silicon)
# when loading PyTorch, ONNX Runtime, and FAISS simultaneously.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
