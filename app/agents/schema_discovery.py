from typing import Any

from app.agents.base import (
    AgentContext,
    AgentProvenance,
    AgentResult,
    BaseAgent,
)


class SchemaDiscoveryAgent(BaseAgent):
    name = "schema_discovery"

    def __init__(self, salesforce_client: Any) -> None:
        self.client = salesforce_client

    def run(self, context: AgentContext) -> AgentResult:
        try:
            user_id = getattr(context, "user_id", None)

            accessible_objects = list(
                self.client.get_accessible_objects(user_id=user_id)
            )

            object_metadata: dict[str, Any] = {}

            for object_name in accessible_objects:
                object_metadata[object_name] = (
                    self.client.describe_object(object_name)
                )

            metadata = getattr(context, "metadata", None)
            if metadata is None:
                metadata = {}
                context.metadata = metadata

            metadata["accessible_objects"] = accessible_objects
            metadata["object_metadata"] = object_metadata

            return AgentResult(
                status="success",
                output={"metadata": {
                    "accessible_objects": accessible_objects,
                    "object_metadata": object_metadata,
                }},
                provenance=AgentProvenance(
                    agent_name=self.name,
                    input_request_id=context.request_id,
                    source_refs=("salesforce_metadata",),
                ),
                validation_status="passed",
            )

        except Exception as exc:
            return AgentResult(
                status="error",
                output={},
                error=f"Schema discovery failed: {exc}",
                validation_status="failed",
            )