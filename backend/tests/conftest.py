"""Test fixtures.

DATA_DIR must be set before anything imports ``app`` (settings are read at
import time and cached), so we do it here at conftest import.
"""

import os
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="caption-test-"))
os.environ.setdefault("CAPTION_STATIC_DIR", "/nonexistent")  # force API-only mode
