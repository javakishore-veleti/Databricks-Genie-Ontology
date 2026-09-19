"""Google ADK fraud detection package.

The facade is the only entry FastAPI uses. It invokes the ADK root agent
(10 specialist sub-agents) which call the shared MCP tools on OLTP + dims/facts.
"""

from ecommerce_genie_ontology.agents_google_adk.facade import GoogleAdkFraudAgentFacadeImpl

__all__ = ["GoogleAdkFraudAgentFacadeImpl"]
