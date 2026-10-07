"""core/causal/taxonomy.py: Hierarchical 6-Tier Failure Taxonomy."""

from enum import Enum
from typing import Dict, List
from core.models.schema import FailureCategory


class FailureSubcategory(str, Enum):
    # 1. Planning
    PLAN_WRONG_DECOMPOSITION = "wrong_decomposition"
    PLAN_MISSING_STEP = "missing_step"
    PLAN_SUPERFLUOUS_ACTION = "superfluous_action"
    PLAN_DEPENDENCY_INVERSION = "dependency_inversion"

    # 2. Tool
    TOOL_SELECTION_ERROR = "tool_selection_error"
    TOOL_SCHEMA_VIOLATION = "argument_schema_hallucination"
    TOOL_RUNTIME_ERROR = "unhandled_runtime_error"
    TOOL_PREMATURE_ABANDONMENT = "premature_abandonment"

    # 3. Context & Memory
    MEMORY_IRRELEVANT_RETRIEVAL = "irrelevant_retrieval"
    MEMORY_MISSING_PRIOR_FACT = "missing_prior_fact"
    MEMORY_STALE_OR_CONTRADICTORY = "stale_or_contradictory"
    MEMORY_NOT_UTILIZED = "memory_not_utilized"

    # 4. Reasoning & State
    REASONING_UNSUPPORTED_INFERENCE = "unsupported_inference"
    REASONING_HALLUCINATED_STATE = "hallucinated_state"
    REASONING_STATE_INCONSISTENCY = "state_inconsistency"

    # 5. Environment
    ENV_TIMEOUT = "timeout"
    ENV_RATE_LIMIT = "rate_limit_429"
    ENV_SYSTEM_MUTATION = "external_system_mutation"

    # 6. Outcome
    OUTCOME_INCOMPLETE = "incomplete_task"
    OUTCOME_FACTUALLY_INCORRECT = "factually_incorrect"
    OUTCOME_POLICY_VIOLATION = "policy_violation"


class FailureTaxonomy:
    """Taxonomy helper for categories and mapping."""

    CATEGORY_MAP: Dict[FailureCategory, List[FailureSubcategory]] = {
        FailureCategory.PLANNING: [
            FailureSubcategory.PLAN_WRONG_DECOMPOSITION,
            FailureSubcategory.PLAN_MISSING_STEP,
            FailureSubcategory.PLAN_SUPERFLUOUS_ACTION,
            FailureSubcategory.PLAN_DEPENDENCY_INVERSION,
        ],
        FailureCategory.TOOL: [
            FailureSubcategory.TOOL_SELECTION_ERROR,
            FailureSubcategory.TOOL_SCHEMA_VIOLATION,
            FailureSubcategory.TOOL_RUNTIME_ERROR,
            FailureSubcategory.TOOL_PREMATURE_ABANDONMENT,
        ],
        FailureCategory.CONTEXT_MEMORY: [
            FailureSubcategory.MEMORY_IRRELEVANT_RETRIEVAL,
            FailureSubcategory.MEMORY_MISSING_PRIOR_FACT,
            FailureSubcategory.MEMORY_STALE_OR_CONTRADICTORY,
            FailureSubcategory.MEMORY_NOT_UTILIZED,
        ],
        FailureCategory.REASONING_STATE: [
            FailureSubcategory.REASONING_UNSUPPORTED_INFERENCE,
            FailureSubcategory.REASONING_HALLUCINATED_STATE,
            FailureSubcategory.REASONING_STATE_INCONSISTENCY,
        ],
        FailureCategory.ENVIRONMENT: [
            FailureSubcategory.ENV_TIMEOUT,
            FailureSubcategory.ENV_RATE_LIMIT,
            FailureSubcategory.ENV_SYSTEM_MUTATION,
        ],
        FailureCategory.OUTCOME: [
            FailureSubcategory.OUTCOME_INCOMPLETE,
            FailureSubcategory.OUTCOME_FACTUALLY_INCORRECT,
            FailureSubcategory.OUTCOME_POLICY_VIOLATION,
        ],
    }
