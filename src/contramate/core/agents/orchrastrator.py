from typing import Union
from contramate.llm import OpenAIChatClient
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
    

