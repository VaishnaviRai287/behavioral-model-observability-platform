from app.ml.base_wrapper import BaseModelWrapper
from app.ml.loader import load_model

# Module-level dict: file_path → loaded wrapper
# Lives for the lifetime of the process.
_cache: dict[str, BaseModelWrapper] = {}


def get_cached_wrapper(file_path: str) -> BaseModelWrapper:
    """
    Return a loaded model wrapper, loading from disk only on first call.

    On subsequent calls with the same file_path, returns the cached wrapper
    without any disk I/O.

    Args:
        file_path: Absolute path to the model file.

    Returns:
        A loaded BaseModelWrapper subclass (SklearnWrapper, PyTorchWrapper, etc.)
    """
    if file_path not in _cache:
        _cache[file_path] = load_model(file_path)
    return _cache[file_path]


def invalidate(file_path: str) -> None:
    """
    Remove a model from the cache.

    Call this when a model is deleted so the stale wrapper is evicted.
    The next call to get_cached_wrapper() with the same path will reload from disk.
    """
    _cache.pop(file_path, None)   # pop with default avoids KeyError if not cached


def clear_all() -> None:
    """
    Clear the entire cache.

    Used in tests to ensure clean state between test runs.
    Do NOT call this in production code.
    """
    _cache.clear()


def cache_size() -> int:
    """Return the number of models currently in cache."""
    return len(_cache)
