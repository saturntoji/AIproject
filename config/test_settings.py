import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-key")

from config.settings import *  # noqa: E402,F403

# В тестах статика не собирается, поэтому WhiteNoise не нужен.
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405
