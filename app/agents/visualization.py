# app/agents/visualization.py

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
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
    METRIC_LABELS: ClassVar[dict[str, str]] = {
        "annualrevenue": "Annual Revenue",
        "revenue": "Revenue",
        "amount": "Sales Amount",
        "opportunitycount": "Opportunity Count",
        "recordcount": "Record Count",
        "count": "Count",
        "industry": "Industry",
        "leadsource": "Lead Source",
        "region": "Region",
        "stagename": "Stage",
        "month": "Month",
        "closedate": "Close Date",
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
            if self._is_numeric_column(column, rows)
        ]

        date_columns = [
            column for column in columns if self._is_date_column(column, rows)
        ]

        y_field = self._select_metric(numeric_columns, context.user_question)
        x_field = self._select_dimension(columns, numeric_columns, date_columns)
        requested_type = self._requested_chart_type(context.user_question)

        if not y_field or not x_field:
            chart_type = "table"
        elif requested_type:
            chart_type = requested_type
        elif date_columns:
            chart_type = "line"
            x_field = date_columns[0]
        else:
            chart_type = "bar"

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

    @staticmethod
    def _is_numeric_column(
        column: str,
        rows: list[dict[str, Any]],
    ) -> bool:
        values = [row.get(column) for row in rows if row.get(column) is not None]
        if not values:
            return False

        for value in values:
            if isinstance(value, bool):
                return False
            try:
                number = Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError):
                return False
            if not number.is_finite():
                return False

        return True

    @staticmethod
    def _select_metric(
        numeric_columns: list[str],
        question: str,
    ) -> str | None:
        if not numeric_columns:
            return None

        normalized_question = question.lower()
        semantic_terms = (
            ("count", ("count", "number of", "how many")),
            ("revenue", ("revenue", "sales")),
            ("amount", ("amount", "value", "pipeline")),
        )
        for metric, terms in semantic_terms:
            if any(term in normalized_question for term in terms):
                match = next(
                    (
                        column
                        for column in numeric_columns
                        if metric in column.lower()
                        or (metric == "count" and column.lower().endswith("count"))
                    ),
                    None,
                )
                if match:
                    return match

        return next(
            (
                column
                for column in numeric_columns
                if column.lower() not in {"id", "ownerid"}
                and not column.lower().endswith("id")
            ),
            numeric_columns[0],
        )

    @staticmethod
    def _select_dimension(
        columns: list[str],
        numeric_columns: list[str],
        date_columns: list[str],
    ) -> str | None:
        if date_columns:
            return date_columns[0]

        return next(
            (
                column
                for column in columns
                if column not in numeric_columns
            ),
            next((column for column in columns if column not in numeric_columns), None),
        )

    @staticmethod
    def _requested_chart_type(question: str) -> str | None:
        normalized = question.lower()
        padded = f" {normalized} "
        if any(term in normalized for term in ("donut", "doughnut", "circular")):
            return "donut"
        if any(term in normalized for term in ("pie", "circle chart")):
            return "pie"
        if any(
            term in normalized for term in ("line chart", "line graph", "trend")
        ) or " line " in padded:
            return "line"
        if any(
            term in normalized
            for term in ("bar chart", "bar graph", "column chart")
        ) or " bar " in padded:
            return "bar"
        return None

    @classmethod
    def _field_label(cls, field: str) -> str:
        normalized = field.lower().replace("_", "")
        return cls.METRIC_LABELS.get(
            normalized,
            field.replace("__c", "").replace("_", " ").strip(),
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
        x_values = [row.get(x_field) for row in rows]
        y_values = [float(Decimal(str(row[y_field]))) for row in rows]
        x_label = self._field_label(x_field)
        y_label = self._field_label(y_field)

        if chart_type in {"pie", "donut"}:
            trace = {
                "type": "pie",
                "labels": [
                    str(value) if value is not None else "Unknown"
                    for value in x_values
                ],
                "values": y_values,
                "hole": 0.5 if chart_type == "donut" else 0,
                "hovertemplate": (
                    f"%{{label}}<br>{y_label}: %{{value:,.2f}}"
                    " (%{percent})<extra></extra>"
                ),
            }
        else:
            trace = {
                "type": "scatter" if chart_type == "line" else "bar",
                **({"mode": "lines+markers"} if chart_type == "line" else {}),
                "x": [
                    str(value) if value is not None else "Unknown"
                    for value in x_values
                ],
                "y": y_values,
                "name": y_label,
                "hovertemplate": (
                    f"{x_label}: %{{x}}<br>{y_label}: %{{y:,.2f}}<extra></extra>"
                ),
            }

        return {
            "chart_type": chart_type,
            "x_field": x_field,
            "y_field": y_field,
            "x_label": x_label,
            "y_label": y_label,
            "data": [trace],
            "layout": {
                "title": {"text": f"{y_label} by {x_label}"},
                **(
                    {}
                    if chart_type in {"pie", "donut"}
                    else {
                        "xaxis": {
                            "title": {"text": x_label},
                            "type": (
                                "date"
                                if x_field.lower() in self.DATE_FIELDS
                                else "category"
                            ),
                        },
                        "yaxis": {
                            "title": {"text": y_label},
                            "tickformat": ",.2f",
                            "tickprefix": (
                                "$"
                                if any(
                                    term in y_field.lower()
                                    for term in ("revenue", "amount", "sales")
                                )
                                else ""
                            ),
                            "separatethousands": True,
                        },
                    }
                ),
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
