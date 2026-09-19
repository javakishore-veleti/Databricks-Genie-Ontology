"""FastAPI entry: HTTP routers and services resolved through ApiObjectsFactory."""

from ecommerce_genie_ontology.api.app import app, create_app
from ecommerce_genie_ontology.api.objects_factory import ApiObjectsFactory

__all__ = ["ApiObjectsFactory", "app", "create_app"]
