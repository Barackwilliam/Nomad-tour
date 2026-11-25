"""Small content cache.

Public pages need data from the remote Supabase database. Instead of querying it on
every visit, page data is cached and every save in the dashboard bumps a version
number, so visitors see changes immediately while normal visits hit the cache.
"""
from django.core.cache import cache

VERSION_KEY = "content-version"


def version():
    v = cache.get(VERSION_KEY)
    if v is None:
        v = 1
        cache.set(VERSION_KEY, v, None)
    return v


def bump():
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 2, None)


def cached(key, fn, timeout=60 * 30):
    full = f"{key}:v{version()}"
    value = cache.get(full)
    if value is None:
        value = fn()
        cache.set(full, value, timeout)
    return value
