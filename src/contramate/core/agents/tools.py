import logging
from enum import StrEnum
from contramate.utils.settings.core import settings
from sqlmodel import Session, create_engine, select
import json
import pandas as pd

# TODO: These models need to be implemented in contramate
# from contramate.models.doc_summery import ContractSummary
# from contramate.models.doc_metadata import ContractMetadata
# from contramate.vectordb.utils import get_vector_store


class SummaryType(StrEnum):
    """Summary types to query from databse"""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"

logger = logging.getLogger(__name__)

answer_given_description = {
    "type": "function",
    "function": {
        "name": "answer_given",
        "description": "If the conversation already contains a complete answer to the question, "
        "use this tool to extract it. Additionally, if the user engages in small talk, "
        "use this tool to remind them that you can only answer questions about contracts.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Respond directly with the answer",
                }
            },
            "required": ["answer"],
        },
    },
}


def answer_given(answer: str):
    """Extract the answer from a given text."""
    logger.info("Answer found in text: %s", answer)
    return answer


respond_unrelated_question_description = {
    "type": "function",
    "function": {
        "name": "respond_unrelated_question",
        "description": "Respond with a message if the question is not related to the source document.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The user question or query to find the answer for",
                }
            },
            "required": ["question"],
        },
    },
}


def respond_unrelated_question_tool(question: str):
    return f"The source document does not contain the answer to the question: {question}"



vectordb_retriver_tool_description = {
    "type": "function",
    "function": {
        "name": "retriver_tool",
        "description": "Query the vector database with a user question to pull the most relevant chunks. When other tools don't fit, fallback to use this one.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The user question or query to find the answer for",
                }
            },
            "required": ["question"],
        },
    },
}


def vector_db_retriver_tool(question: str) -> str:
    """Query the database with a user question."""
    logger.info("=== Entering Retrival Tool ===")
    try:
        # TODO: Implement vector store functionality for contramate
        logger.warning("Vector store not yet implemented in contramate")
        return f"Vector search functionality not yet available. Question was: {question}"
    except Exception as e:
        return f"Could not query vector store, cause an error: {e}"
    

sumery_retriver_tool_description = {
    "type": "function",
    "function": {
        "name": "summery_retriver_tool",
        "description": "Query the database with a user provide cwid and summary type to pull the most relevant summary. The tool is only when only user ask to get summary of a contract.",
        "parameters": {
            "type": "object",
            "properties": {
                "cwid": {
                    "type": "string",
                    "description": "The CWID of the contract",
                },
                "summary_type": {
                    "type": "string",
                    "enum": ["short", "medium", "long"],
                }
            },
            "required": ["cwid", "summary_type"],
        },
    },
}


def summery_retriver_tool(cwid: str, summary_type: SummaryType = SummaryType.SHORT) -> str:
    logger.info("=== Entering Summery Retrival Tool ===")
    logger.info(f"Retrieving {summary_type} summary for contract with CWID: {cwid}")

    try:
        # TODO: Implement ContractSummary model and database connection
        logger.warning("Contract summary functionality not yet implemented in contramate")
        return f"Contract summary functionality not yet available. CWID: {cwid}, Type: {summary_type}"
    except Exception as e:
        return f"Could not retrieve summary, cause an error: {e}"
    

compare_contract_tool_description = {
    "type": "function",
    "function": {
        "name": "compare_contract_tool",
        "description": "Query the database with a list of CWID to compare the contracts. The tool is only when only user ask to compare contracts.",
        "parameters": {
            "type": "object",
            "properties": {
                "cwid": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "The CWID of the contracts to compare",
                }
            },
            "required": ["cwid"],
        },
    },
}

def compare_contract_tool(cwid: list[str]) -> str:
    logger.info("=== Entering Compare Contract Tool ===")
    logger.info(f"Comparing following contracts: {cwid}")

    try:
        # TODO: Implement ContractMetadata model and database connection
        logger.warning("Contract comparison functionality not yet implemented in contramate")
        return f"Contract comparison functionality not yet available. CWIDs: {', '.join(cwid)}"
    except Exception as e:
        return f"Could not compare contracts, cause an error: {e}"
    

_tools = {
    "retriver_tool": {
        "description": vectordb_retriver_tool_description,
        "function": vector_db_retriver_tool
    },
    # "answer_given": {
    #     "description": answer_given_description,
    #     "function": answer_given
    # },
    "summery_retriver_tool": {
        "description": sumery_retriver_tool_description,
        "function": summery_retriver_tool
    },
    "compare_contract_tool": {
        "description": compare_contract_tool_description,
        "function": compare_contract_tool
    },
    # "respond_unrelated_question": {
    #     "description": respond_unrelated_question_description,
    #     "function": respond_unrelated_question_tool
    # }
}



def handle_tool_calls(llm_tool_calls: list[dict[str, any]]):
    logger.info("=== Selecting Tools ===")
    output = []
    available_tools = [tool["description"]["function"]["name"] for tool in _tools.values()]
    if llm_tool_calls:
        tool_list = [tool_call.function.name for tool_call in llm_tool_calls]
        logger.info(f"Follwing tools are selected for execution: {tool_list} from available tools: {available_tools}")
        for tool_call in llm_tool_calls:
            function_to_call = _tools[tool_call.function.name]["function"]
            function_args = json.loads(tool_call.function.arguments)
            res = function_to_call(**function_args)
            output.append(res)
    logger.info(f"Tool execution finished!")
    return output


def get_tool_descriptions() -> list[str]:
    description = [tool["description"] for tool in _tools.values()]
    return description


if __name__ == "__main__":
    print(get_tool_descriptions())
