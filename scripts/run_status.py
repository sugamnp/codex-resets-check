from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import json
import re
import urllib.request
from pathlib import Path

TRACKERS = [
    ("Codex Resets", "https://codex-resets.com/"),
    ("CodexResets", "https://codexresets.com/"),
    ("Codex Reset Monitor", "https://codexreset.org/"),
    ("Reset Alert