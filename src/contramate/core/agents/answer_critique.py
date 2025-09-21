import logging
from contramate.utils.clients.ai.openai_client import OpenAIChatClient
import json


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
    You are an expert at identifying if questions has been fully answered or if there is an opportunity to enrich the answer.
    The user will provide a question, and you will scan through the provided information to see if the question is answered.
    If anything is missing from the answer, you will provide a set of new questions that can be asked to gather the missing information.
    All new questions must be complete, atomic and specific.
    - If user ask for summery of a certain contract as the summery is pulled by the tool you will respond with an empty list.
    - If user ask to compare contrats as the comparison is done by the tool you will respond with an empty list.
    However, if the provided information is enough to answer the original question, you will respond with an empty list.
    

    JSON template to use for finding missing information:
    {
        "questions": ["question1", "question2"]
    }
    JSON template to use when user asked for summery:
    {
        "questions": []
    }
    JSON template to use when user asked to compare contrats:
    {
        "questions": []
    }
"""

class AnswerCritiqueAgent:
    def __init__(self, client: OpenAIChatClient, system_prompt: str | None = None):
        self.client = client
        self.system_prompt = system_prompt if system_prompt else SYSTEM_PROMPT


    def execute(self, question: str, answers: list[dict[str, str]]) -> list[str]:
        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            *answers,
            {
                "role": "user",
                "content": f"The original user question to answer: {question}",
            },
        ]
        config = {"response_format": {"type": "json_object"}}
        output = self.client.chat(messages, config=config)
        logger.info(f"Answer critique response: {output}")
        try:
            return json.loads(output)["questions"]
        except json.JSONDecodeError:
            print("Error decoding JSON")
        return []
    
    def __call__(self, input: str, answers: list[dict[str, str]] = None) -> list[str]:
        return self.execute(input, answers)