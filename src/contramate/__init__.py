"""Contramate CLI - Interactive chat application for contract understanding"""

from typing import Dict, List, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
import logging

from contramate.llm import LLMClientFactory, BaseChatClient

# Initialize Typer app and Rich console
app = typer.Typer(
    name="contramate",
    help="Interactive chat application for contract understanding",
    add_completion=False
)
console = Console()
logger = logging.getLogger(__name__)

# Default system prompt for markdown responses
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant.
Please format your responses using markdown for better readability.
Use appropriate markdown features like:
- **bold** for emphasis
- *italic* for subtle emphasis
- `code` for inline code or technical terms
- ```language code blocks``` for multi-line code
- # Headers for organizing content
- - Bullet points for lists
- 1. Numbered lists for sequential items
- > Blockquotes for important notes

Keep your responses clear, well-structured, and easy to read."""


class ChatSession:
    """Manages chat session with in-memory message history"""

    def __init__(self, client: BaseChatClient):
        """
        Initialize chat session

        Args:
            client: LLM client to use for chat
        """
        self.client = client
        self.messages: List[Dict[str, str]] = []
        self.session_active = True

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the session history

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get the current message history

        Returns:
            List of message dictionaries
        """
        return self.messages.copy()

    def clear_history(self) -> None:
        """Clear the message history"""
        self.messages.clear()
        console.print("[yellow]Chat history cleared![/yellow]")

    def chat(self, user_message: str) -> str:
        """
        Send a message and get a response

        Args:
            user_message: User's message

        Returns:
            Assistant's response
        """
        # Add user message to history
        self.add_message("user", user_message)

        try:
            # Get response from client with full history
            response = self.client.chat(
                messages=self.messages,
            )

            # Add assistant response to history
            self.add_message("assistant", response)

            return response

        except Exception as e:
            logger.error(f"Error during chat: {e}")
            error_msg = f"Error: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return error_msg


def display_welcome(client_type: str) -> None:
    """Display welcome message"""
    welcome_text = f"""
# Welcome to Contramate Chat! 🤖

**Client Type:** {client_type}

Type your messages to chat. Special commands:
- `/history` - Show conversation history
- `/clear` - Clear conversation history
- `/quit` or `/exit` - Exit the application
- `/help` - Show this help message

Start chatting below!
"""
    console.print(Panel(Markdown(welcome_text), box=box.ROUNDED, border_style="blue"))


def display_help() -> None:
    """Display help information"""
    help_text = """
# Contramate Chat Commands

- `/history` - Show conversation history
- `/clear` - Clear conversation history
- `/quit` or `/exit` - Exit the application
- `/help` - Show this help message
"""
    console.print(Panel(Markdown(help_text), box=box.ROUNDED, border_style="cyan"))


def display_history(messages: List[Dict[str, str]]) -> None:
    """Display conversation history (excluding system messages)"""
    # Filter out system messages
    user_assistant_messages = [msg for msg in messages if msg["role"] != "system"]

    if not user_assistant_messages:
        console.print("[yellow]No messages in history.[/yellow]")
        return

    console.print("\n[bold cyan]Conversation History:[/bold cyan]")
    message_number = 0
    for msg in user_assistant_messages:
        message_number += 1
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            console.print(f"\n[bold cyan]User (message {message_number}):[/bold cyan]")
            console.print(Panel(Markdown(content), border_style="cyan", box=box.SIMPLE))
        elif role == "assistant":
            console.print(f"\n[bold green]Assistant (message {message_number}):[/bold green]")
            console.print(Panel(Markdown(content), border_style="green", box=box.SIMPLE))


@app.command()
def chat(
    client_type: str = typer.Option(
        "litellm",
        "--client",
        "-c",
        help="Client type to use: litellm, openai, or azure_openai"
    ),
    system_prompt: Optional[str] = typer.Option(
        None,
        "--system",
        "-s",
        help="Optional system prompt to initialize the conversation"
    )
) -> None:
    """
    Start an interactive chat session with Contramate

    Use the --client option to choose between litellm (default), openai, or azure_openai.
    """
    try:
        # Validate client type
        if client_type not in ["litellm", "openai", "azure_openai"]:
            console.print(f"[red]Error: Invalid client type '{client_type}'. Must be one of: litellm, openai, azure_openai[/red]")
            raise typer.Exit(1)

        # Initialize client factory and create client
        console.print(f"[cyan]Initializing {client_type} client...[/cyan]")
        factory = LLMClientFactory.create_from_default(client_type)  # type: ignore
        llm_client = factory.create_client()
        console.print("[green]✓ Client initialized successfully![/green]\n")

        # Create chat session
        session = ChatSession(llm_client)

        # Add system prompt (use default if not provided)
        prompt_to_use = system_prompt if system_prompt else DEFAULT_SYSTEM_PROMPT
        session.add_message("system", prompt_to_use)
        if system_prompt:
            console.print(f"[dim]Custom system prompt set[/dim]\n")
        else:
            console.print(f"[dim]Using default system prompt for markdown responses[/dim]\n")

        # Display welcome message
        display_welcome(client_type)

        # Main chat loop
        while session.session_active:
            try:
                # Get user input
                console.print()
                user_input = console.input("[bold cyan]You:[/bold cyan] ")

                # Handle empty input
                if not user_input.strip():
                    continue

                # Handle special commands
                if user_input.strip().startswith("/"):
                    command = user_input.strip().lower()

                    if command in ["/quit", "/exit"]:
                        console.print("\n[yellow]Goodbye! 👋[/yellow]")
                        break
                    elif command == "/help":
                        display_help()
                        continue
                    elif command == "/history":
                        display_history(session.get_history())
                        continue
                    elif command == "/clear":
                        session.clear_history()
                        continue
                    else:
                        console.print(f"[red]Unknown command: {command}[/red]")
                        console.print("[dim]Type /help for available commands[/dim]")
                        continue

                # Get response from chat session
                console.print("\n[bold green]Assistant[/bold green]")
                with console.status("[cyan]Thinking...[/cyan]"):
                    response = session.chat(user_input)

                # Display response
                console.print(Panel(Markdown(response), border_style="green", box=box.SIMPLE))

            except KeyboardInterrupt:
                console.print("\n\n[yellow]Chat interrupted. Type /quit to exit or continue chatting.[/yellow]")
                continue
            except Exception as e:
                logger.error(f"Error in chat loop: {e}")
                console.print(f"[red]Error: {str(e)}[/red]")
                console.print("[dim]Type /quit to exit or continue chatting.[/dim]")

    except Exception as e:
        logger.error(f"Failed to initialize chat: {e}")
        console.print(f"[red]Failed to initialize chat: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show Contramate version"""
    console.print("[bold blue]Contramate[/bold blue] version [green]0.1.0[/green]")


def main() -> None:
    """Entry point for the CLI application"""
    app()


if __name__ == "__main__":
    main()
