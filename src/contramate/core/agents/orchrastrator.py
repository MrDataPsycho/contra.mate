from typing import Union
from contramate.llm import OpenAIChatClient, LiteLLMChatClient
from contramate.core.agents.query_rewriter import QueryRewriterAgent
from contramate.core.agents.tool_executor import ToolExecutorAgent
from contramate.core.agents.answer_critique import AnswerCritiqueAgent
import json
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Your job is to help the user with their questions.
You will receive user questions and information needed to answer the questions
If the information is missing to answer part of or the whole question, you will say that the information 
is missing. You will only use the information provided to you in the prompt to answer the questions.
You are not allowed to make anything up or use external information.
"""

class OrchrastratorAgent:
    def __init__(self, client: Union[OpenAIChatClient, LiteLLMChatClient], system_prompt: str | None = None):
        self.client = client
        self.system_prompt = system_prompt if system_prompt else SYSTEM_PROMPT
        self.query_rewriter_agent = QueryRewriterAgent(client)
        self.tool_selector_agent = ToolExecutorAgent(client)
        self.answer_critique_agent = AnswerCritiqueAgent(client)

    def chat(self, input: str, conversation_history: list[dict[str, str]]):  
        logger.info(f"User input: {input}, with initial No. of User and Assistant turns: {len(conversation_history)}")
        updated_question = self.query_rewriter_agent(input, conversation_history)

        response  = self.tool_selector_agent(updated_question, conversation_history)
        conversation_history.append({"role": "assistant", "content": f"For the question: '{updated_question}', we have the answer: '{json.dumps(response)}'"})
        return conversation_history


    def execute(self, input: str, conversation_history: list[dict[str, str]] = None):
        conversation_history = conversation_history if conversation_history else []
        conversation_history = self.chat(input, conversation_history)
        critique = self.answer_critique_agent(input, conversation_history)

        if critique:
            conversation_history = self.chat(" ".join(critique), conversation_history)

        llm_response = self.client.chat(
            [
                {"role": "system", "content": self.system_prompt},
                *conversation_history,
                {"role": "user", "content": f"The user question to answer: {input}"},
            ],
        )

        return llm_response
    
    def __call__(self, input: str, conversation_history: list[dict[str, str]] = None) -> str:
        return self.execute(input, conversation_history)
    

if __name__ == "__main__":
    from contramate.utils.settings.core import settings
    import logging

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO
    )

    client = OpenAIChatClient()
    agent = OrchrastratorAgent(client)
    query = "What do you know about Supplier: Alpha Suppliers Inc. and what it supplies?"
    response = agent(query)
    print(response)
    

