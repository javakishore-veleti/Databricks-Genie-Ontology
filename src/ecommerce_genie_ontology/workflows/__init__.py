"""Workflows: class-based runners resolved through WorkflowsObjectsFactory."""

__all__ = ["WorkflowOrchestrator", "WorkflowsObjectsFactory"]


def __getattr__(name: str):
    if name == "WorkflowsObjectsFactory":
        from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory

        return WorkflowsObjectsFactory
    if name == "WorkflowOrchestrator":
        from ecommerce_genie_ontology.workflows.orchestrator import WorkflowOrchestrator

        return WorkflowOrchestrator
    raise AttributeError(name)
