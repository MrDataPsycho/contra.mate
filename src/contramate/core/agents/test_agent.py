import asyncio
from contramate.llm import LLMVanillaClientFactory
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic import BaseModel

class ResponseModel(BaseModel):
    answer: str
    summery: str

async def test_agent():
    """Simple test agent that says hello to AI"""
    factory = LLMVanillaClientFactory()
    client = factory.get_default_client(async_mode=True)
    provider = OpenAIProvider(openai_client=client)

    model = OpenAIChatModel(
        "gpt-4.1-mini",
        provider=provider,
    )

    agent = Agent(
        model=model,
        system_prompt="You are a friendly AI assistant. You always respond with properly formatted Markdown.",
    )
    result = await agent.run("What are the main benefits of cloud computing?")

    # Access the response data and metadata
    print("Agent response type:", type(result.output))
    print("\nAnswer:", result.output)
    print("\n--- Usage Information ---")

    # Access usage info
    usage = result.usage()
    print(f"Input tokens: {usage.input_tokens}")
    print(f"Output tokens: {usage.output_tokens}")
    print(f"Total tokens: {usage.total_tokens}")

    # Access the underlying model response for additional details
    if result.new_messages():
        last_response = result.new_messages()[-1]
        print(f"\nMessage timestamp: {last_response.timestamp}")
        print(f"Stop reason: {last_response.finish_reason}")
        print(f"Message ID: {last_response.provider_response_id}")
        print(f"Model name: {last_response.model_name}")
    

if __name__ == "__main__":
    asyncio.run(test_agent())

