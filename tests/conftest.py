from __future__ import annotations

import sys
from pathlib import Path

# Ensure local package imports work even if pytest is invoked from a different cwd.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

