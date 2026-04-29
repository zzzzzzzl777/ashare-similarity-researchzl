"""A-share K-line similarity retrieval system."""

from __future__ import annotations

import os

# Keep Polars/Rayon from over-spawning threads on Windows workstations that are
# also running GPU training jobs. These env vars must be present before Polars
# is imported by any submodule.
os.environ.setdefault("POLARS_MAX_THREADS", "2")
os.environ.setdefault("RAYON_NUM_THREADS", "2")

__all__ = ["__version__"]

__version__ = "0.1.0"
