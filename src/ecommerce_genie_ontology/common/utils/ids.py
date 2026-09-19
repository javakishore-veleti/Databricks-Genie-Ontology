from __future__ import annotations

import hashlib


def hex32(seed: str) -> str:
    return hashlib.md5(f"ecommerce-genie-ontology:{seed}".encode("utf-8")).hexdigest()
