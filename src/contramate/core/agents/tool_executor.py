import logging
from typing import Union
from contramate.llm import OpenAIChatClient, LiteLLMChatClient
from contramate.core.agents.tools import handle_tool_calls, get_tool_descriptions


logger = logging.getLogger(__name__)

    
SYSTEM_PROMPT = """
    Your job is to chose the right tool needed to respond to the user question. 
    The available tools are provided to you in the prompt.
    Make sure to pass the right and the complete arguments to the chosen tool.
"""


class ToolExecutorAgent:
    def __init__(self, client: Union[OpenAIChatClient, LiteLLMChatClient], system_prompt: str | None = None):
        self.client = client
        self.system_prompt = system_prompt if system_prompt else SYSTEM_PROMPT

    def execute(self, question: str, conversation_history: list[dict[str, str]]):
        logger.info("=== Entering Tool Selector Router ===")
        llm_tool_calls = self.client.select_tool(
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                *conversation_history,
                {
                    "role": "user",
                    "content": f"The user question or satement to find a tool to answer: '{question}'",
                },
            ],
            tools=get_tool_descriptions(),
        )
        return handle_tool_calls(llm_tool_calls)
    
    def __call__(self, input: str, conversation_history: list[dict[str, str]] = None) -> list:
        return self.execute(input, conversation_history or [])