"""Settings for the test run: development defaults, no secrets required."""

import os

os.environ.setdefault("DJANGO_DEBUG", "1")

from esteira.settings import *  # noqa: E402, F403

# Hashing passwords at production strength would dominate the test run.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
