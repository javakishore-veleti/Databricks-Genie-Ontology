from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
src = ROOT / "src"
if src.is_dir():
    sys.path.insert(0, str(src))

from ecommerce_genie_ontology.mcp.server import main

if __name__ == "__main__":
    main(["--http"])
