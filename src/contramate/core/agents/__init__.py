"""Core agents for contract processing."""

from contramate.core.agents.metadata_parser import (
    MetadataParserAgent,
    ContractMetadata,
)
from contramate.core.agents.factory import PyadanticAIModelUtilsFactory
from contramate.core.agents.query_rewriter import (
    QueryRewriterAgentFactory,
    QueryRewriteResponse,
)
from contramate.core.agents.answer_critique import (
    AnswerCritiqueAgent,
    AnswerCritiqueResponse,
)
from contramate.core.agents.talk_to_contract import (
    TalkToContractAgentFactory,
    TalkToContractResponse,
    TalkToContractDependencies,
)

__all__ = [
    "MetadataParserAgent",
    "ContractMetadata",
    "PyadanticAIModelUtilsFactory",
    "QueryRewriterAgentFactory",
    "QueryRewriteResponse",
    "AnswerCritiqueAgent",
    "AnswerCritiqueResponse",
    "TalkToContractAgentFactory",
    "TalkToContractResponse",
    "TalkToContractDependencies",
]
