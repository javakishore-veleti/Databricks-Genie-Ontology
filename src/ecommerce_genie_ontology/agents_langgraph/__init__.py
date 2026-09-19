"""LangGraph fraud detection package.

The facade is the only entry FastAPI uses. It invokes a LangGraph StateGraph
that calls the shared MCP tool functions against OLTP + dims/facts.
"""

from ecommerce_genie_ontology.agents_langgraph.facade import LangGraphFraudAgentFacadeImpl

__all__ = ["LangGraphFraudAgentFacadeImpl"]
