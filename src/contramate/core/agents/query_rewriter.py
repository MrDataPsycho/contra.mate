import logging
from typing import Union
from contramate.llm import OpenAIChatClient, LiteLLMChatClient
import json


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are an expert at updating questions to make them ask for one thing only, more atomic, specific and easier to find the answer for.
You do this by filling in missing information in the question, with the extra information provided to you in previous answers. 

You respond with the updated question that has all information in it.
Only edit the question if needed. If the original question already is atomic, specific and easy to answer, you keep the original.
Do not ask for more information than the original question. Only rephrase the question to make it more complete.

JSON template to use:
{
    "question": "question1"
}
"""

class QueryRewriterAgent:
    def __init__(self, client: Union[OpenAIChatClient, LiteLLMChatClient], system_prompt: str | None = None):
        self.client = client
        self.system_prompt = system_prompt if system_prompt else SYSTEM_PROMPT

    def execute(self, input: str, conversation_history: list[dict[str, str]]) -> str:
        logger.info("=== Entering Query Update Node ===")
        if len(conversation_history) == 0:
            logger.info("Query Update endpoint called with Initial User turn")
        else:
            logger.info(f"Query Update endpoint called with Intermediate User and Assistant turns: {len(conversation_history)}")


        messages = [
            {"role": "system", "content": self.system_prompt},
            *conversation_history,
            {"role": "user", "content": f"The user question to rewrite: '{input}'"},
        ]

        config = {"response_format": {"type": "json_object"}}
        output = self.client.chat(messages, config=config, )
        try:
            updated_question = json.loads(output)["question"]
            logger.info(f"Updated Query: {updated_question}")
            return updated_question
        except json.JSONDecodeError:
            print("Error decoding JSON")
        return input  # Return original input if JSON parsing fails
    
    def __call__(self, input: str, conversation_history: list[dict[str, str]] = None) -> str:
        return self.execute(input, conversation_history or [])