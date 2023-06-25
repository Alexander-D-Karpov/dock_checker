from django.core.cache import cache
from rest_framework.exceptions import NotFound


def get_task_status(pk: str) -> dict:
    if cache.get(f"{pk}-processed") is None:
        raise NotFound("given task does not exist")
    created = cache.get_or_set(f"{pk}-processed", 0)
    total = cache.get_or_set(f"{pk}-total", 0)
    features_loaded = cache.get_or_set(f"{pk}-features_loaded", False)
    error = cache.get_or_set(f"{pk}-error", False)
    error_description = cache.get_or_set(f"{pk}-error_description", "")
    return {
        "processed": created,
        "total": total,
        "features_loaded": features_loaded,
        "error": error,
        "error_description": error_description,
    }
