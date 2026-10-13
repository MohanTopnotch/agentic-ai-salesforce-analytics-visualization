
from enum import Enum


class WorkflowState(str, Enum):
    INITIALIZED = "initialized"
    UNDERSTANDING_INTENT = "understanding_intent"
    DISCOVERING_METADATA = "discovering_metadata"
    PLANNING_QUERY = "planning_query"
    EXECUTING_QUERY = "executing_query"
    ANALYZING_RESULTS = "analyzing_results"
    VERIFYING_RESULTS = "verifying_results"
    CREATING_VISUALIZATION = "creating_visualization"
    GENERATING_INSIGHTS = "generating_insights"
    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    FAILED = "failed"