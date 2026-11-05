import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key")

from config.settings import *  # noqa: E402,F403
