from __future__ import annotations

import json

from ecommerce_genie_ontology.common.constants import (
    AGENT_DESCRIPTION,
    AGENT_INSTRUCTIONS,
    SAMPLE_QUESTIONS,
)
from ecommerce_genie_ontology.common.interfaces.create_agents import CreateAgentsWorkspaceFacade
from ecommerce_genie_ontology.common.utils.ids import hex32


def serialized_space(fq: str) -> str:
    metric_views = [
        {
            "identifier": f"{fq}.mv_customer_returns",
            "description": [
                "Certified customer-return measures: return count, units returned, and refunded amount."
            ],
        },
        {
            "identifier": f"{fq}.mv_inventory_health",
            "description": [
                "Certified inventory-health measures: average stock on hand, units received, low-stock snapshots."
            ],
        },
        {
            "identifier": f"{fq}.mv_sales_performance",
            "description": [
                "Certified sales-performance measures: total revenue, units sold, order count, average order value."
            ],
        },
    ]
    sample_questions = sorted(
        ({"id": hex32(f"sample:{question}"), "question": [question]} for question in SAMPLE_QUESTIONS),
        key=lambda item: item["id"],
    )
    example_sqls = sorted(
        [
            {
                "id": hex32("sql:revenue-by-category"),
                "question": ["What was total revenue last quarter by product category?"],
                "sql": [
                    "SELECT product_category, MEASURE(total_revenue) AS total_revenue\n",
                    f"FROM {fq}.mv_sales_performance\n",
                    "WHERE year = year(current_date())\n",
                    "  AND quarter = quarter(add_months(current_date(), -3))\n",
                    "GROUP BY product_category\n",
                    "ORDER BY total_revenue DESC",
                ],
            },
            {
                "id": hex32("sql:aov-by-segment"),
                "question": ["What is the average order value by customer segment?"],
                "sql": [
                    "SELECT customer_segment, MEASURE(avg_order_value) AS avg_order_value\n",
                    f"FROM {fq}.mv_sales_performance\n",
                    "WHERE year = year(current_date())\n",
                    "GROUP BY customer_segment\n",
                    "ORDER BY avg_order_value DESC",
                ],
            },
            {
                "id": hex32("sql:low-stock"),
                "question": ["Which products have the lowest average stock on hand?"],
                "sql": [
                    "SELECT product_category, MEASURE(avg_stock_on_hand) AS avg_stock_on_hand\n",
                    f"FROM {fq}.mv_inventory_health\n",
                    "GROUP BY product_category\n",
                    "ORDER BY avg_stock_on_hand ASC",
                ],
            },
            {
                "id": hex32("sql:return-rate"),
                "question": ["What's our customer return rate this year vs last year?"],
                "sql": [
                    "SELECT r.year,\n",
                    "       r.return_amount / s.total_revenue AS return_rate\n",
                    "FROM (\n",
                    "  SELECT year, MEASURE(return_amount) AS return_amount\n",
                    f"  FROM {fq}.mv_customer_returns\n",
                    "  WHERE year IN (year(current_date()), year(current_date()) - 1)\n",
                    "  GROUP BY year\n",
                    ") r\n",
                    "JOIN (\n",
                    "  SELECT year, MEASURE(total_revenue) AS total_revenue\n",
                    f"  FROM {fq}.mv_sales_performance\n",
                    "  WHERE year IN (year(current_date()), year(current_date()) - 1)\n",
                    "  GROUP BY year\n",
                    ") s ON r.year = s.year",
                ],
            },
        ],
        key=lambda item: item["id"],
    )
    payload = {
        "version": 2,
        "config": {"sample_questions": sample_questions},
        "data_sources": {"metric_views": metric_views},
        "instructions": {
            "text_instructions": [
                {"id": hex32("instructions:retail-analytics"), "content": [AGENT_INSTRUCTIONS]}
            ],
            "example_question_sqls": example_sqls,
        },
    }
    return json.dumps(payload, separators=(",", ":"))


class CreateGenieAgentTask:
    key = "03_create_genie_agent"

    def __init__(self, facade: CreateAgentsWorkspaceFacade) -> None:
        self._facade = facade

    def run(self) -> None:
        space_id = self._facade.upsert_genie_agent(
            serialized_space(self._facade.fq_schema), AGENT_DESCRIPTION
        )
        self._facade.certify_and_tag_agent(space_id)
        print(f"Genie agent '{self._facade.agent_title}' ready ({space_id})")
        print("Attach this id as GENIE_SPACE_ID in .env if you want invoke to skip title lookup.")


def run(facade: CreateAgentsWorkspaceFacade) -> None:
    CreateGenieAgentTask(facade).run()
