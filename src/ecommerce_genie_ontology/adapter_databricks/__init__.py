"""Databricks adapter: DAOs plus facade implementations of common interfaces."""

__all__ = ["AdapterDatabricksObjectsFactory"]


def __getattr__(name: str):
    if name == "AdapterDatabricksObjectsFactory":
        from ecommerce_genie_ontology.adapter_databricks.objects_factory import (
            AdapterDatabricksObjectsFactory,
        )

        return AdapterDatabricksObjectsFactory
    raise AttributeError(name)
