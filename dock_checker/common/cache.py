from django.core.cache import cache


def incr_key(key, value, timeout=None):
    return cache.incr(key, delta=value)


def set_key(key, value, timeout=None):
    return cache.set(key, value, timeout=timeout)


def add_key(key, value, timeout=None):
    return cache.add(key, value, timeout=timeout)


def check_if_key_exists(key):
    return cache.get(key) is not None


def get_key(key):
    return cache.get(key)


def delete_key(key):
    return cache.delete(key)
