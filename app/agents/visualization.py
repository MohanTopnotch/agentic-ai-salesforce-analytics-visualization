# app/agents/visualization.py

from datetime import date, datetime
from typing import Any, ClassVar

from app.agents.base import (
    AgentContext,
    AgentProvenance,
    AgentResult,
    BaseAgent,
)


class VisualizationAgent(BaseAgent):
    name = "visualization"

    DATE_FIELDS: ClassVar[set[str]] = {
        "date",
        "createddate",
        "closedate",
        "activitydate",
        "month",
        "year",
        "period",
    }

    def run(self, context: AgentContext) -> AgentResult:
        rows = context.calculated_data

        # Do not visualize results that failed verification.
        if context.verification.get("status") != "verified":
            return AgentResult(
                status="error",
                output={
                    "diagnostic": ("Visualization requires verified analytical data.")
                },
                provenance=self._provenance(context),
                validation_status="failed",
                # error_message="Analysis verification has not passed.",
                error="Analysis verification has not passed.",
            )

        if not rows:
            spec = {
                "data": [],
                "layout": {
                    "title": {"text": "No data available"},
                    "annotations": [
                        {
                            "text": "No records match the requested analysis.",
                            "showarrow": False,
                            "xref": "paper",
                            "yref": "paper",
                            "x": 0.5,
                            "y": 0.5,
                        }
                    ],
                },
                "config": {"responsive": True},
                "chart_type": "empty",
            }

            context.visualization = spec

            return AgentResult(
                status="success",
                output={"visualization": spec},
                provenance=self._provenance(context),
                validation_status="passed",
            )

        columns = list(dict.fromkeys(key for row in rows for key in row))

        numeric_columns = [
            column
            for column in columns
            if any(
                isinstance(row.get(column), (int, float))
                and not isinstance(row.get(column), bool)
                for row in rows
            )
        ]

        date_columns = [
            column for column in columns if self._is_date_column(column, rows)
        ]

        # A date dimension plus a numeric metric indicates a time series.
        if date_columns and numeric_columns:
            chart_type = "line"
            x_field = date_columns[0]
            y_field = numeric_columns[0]

        # A single numeric metric with a categorical field is a comparison.
        elif numeric_columns and len(columns) == 2:
            chart_type = "bar"
            y_field = numeric_columns[0]
            x_field = next(column for column in columns if column != y_field)

        # Use a table for multiple descriptive columns or raw tabular output.
        else:
            chart_type = "table"
            x_field = None
            y_field = None

        if chart_type == "table":
            spec = self._build_table(rows, columns)
        else:
            spec = self._build_chart(
                rows=rows,
                chart_type=chart_type,
                x_field=x_field,
                y_field=y_field,
            )

        context.visualization = spec

        return AgentResult(
            status="success",
            output={"visualization": spec},
            provenance=self._provenance(context),
            validation_status="passed",
        )

    def _is_date_column(
        self,
        column: str,
        rows: list[dict[str, Any]],
    ) -> bool:
        if column.lower() in self.DATE_FIELDS:
            return True

        values = [row.get(column) for row in rows if row.get(column) is not None]

        if not values:
            return False

        # Require all non-null values to be dates or ISO date strings.
        for value in values:
            if isinstance(value, (date, datetime)):
                continue

            if isinstance(value, str):
                try:
                    date.fromisoformat(value[:10])
                    continue
                except ValueError:
                    return False

            return False

        return True

    def _build_chart(
        self,
        rows: list[dict[str, Any]],
        chart_type: str,
        x_field: str,
        y_field: str,
    ) -> dict[str, Any]:
        x_values = [str(row.get(x_field, "")) for row in rows]
        y_values = [row.get(y_field) for row in rows]

        trace = {
            "type": chart_type,
            "x": x_values,
            "y": y_values,
            "name": y_field,
            "hovertemplate": (
                f"{x_field}: %{{x}}<br>{y_field}: %{{y:,.2f}}<extra></extra>"
            ),
        }

        return {
            "chart_type": chart_type,
            "data": [trace],
            "layout": {
                "title": {"text": f"{y_field} by {x_field}"},
                "xaxis": {
                    "title": {"text": x_field},
                    "type": "date" if chart_type == "line" else "category",
                },
                "yaxis": {
                    "title": {"text": y_field},
                    "tickformat": ",.2f",
                },
                "autosize": True,
                "margin": {"l": 70, "r": 25, "t": 65, "b": 70},
            },
            "config": {
                "responsive": True,
                "displaylogo": False,
            },
        }

    def _build_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str],
    ) -> dict[str, Any]:
        return {
            "chart_type": "table",
            "data": [
                {
                    "type": "table",
                    "header": {
                        "values": columns,
                    },
                    "cells": {
                        "values": [
                            [row.get(column) for row in rows] for column in columns
                        ],
                    },
                }
            ],
            "layout": {
                "title": {"text": "Analytical Results"},
                "autosize": True,
            },
            "config": {
                "responsive": True,
                "displaylogo": False,
            },
        }

    def _provenance(
        self,
        context: AgentContext,
    ) -> AgentProvenance:
        return AgentProvenance(
            agent_name=self.name,
            input_request_id=context.request_id,
            source_refs=("calculated_data", "verification"),
        )
