from app.ml.base_wrapper import BaseModelWrapper
from app.ml.loader import load_model

# file_path -> loaded wrapper, for the lifetime of the process.
_cache: dict[str, BaseModelWrapper] = {}


def get_cached_wrapper(file_path: str) -> BaseModelWrapper:
    """Return a loaded model wrapper, hitting disk only on the first call for a given path."""
    if file_path not in _cache:
        _cache[file_path] = load_model(file_path)
    return _cache[file_path]


def invalidate(file_path: str) -> None:
    """Evict a model from the cache — call this when a model is deleted."""
    _cache.pop(file_path, None)


def clear_all() -> None:
    """Clear the entire cache. Test use only."""
    _cache.clear()


def cache_size() -> int:
    """Return the number of models currently in cache."""
    return len(_cache)
