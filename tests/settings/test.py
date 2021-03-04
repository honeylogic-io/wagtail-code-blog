# pylint: disable=wildcard-import,unused-wildcard-import
from .base import *

SECRET_KEY = "very-secret"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
