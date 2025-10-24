"""
Streamlit UI for Contramate - Contract Chat Assistant

This UI provides:
- Document selection from contract_asmd database
- Conversation management with global filters
- Chat interface with document-aware context
- Message history persistence in DynamoDB
"""

import streamlit as st
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import time
import os

from contramate.ui import format_answer_with_citations_markdown

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_USER_ID = "streamlit_user"  # In production, this would come from authentication


# Helper Functions
def get_documents(limit: int = 1000) -> List[Dict[str, Any]]:
    """Fetch all documents from the API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/contracts/documents", params={"limit": limit})
        response.raise_for_status()
        data = response.json()
        return data.get("documents", [])
    except Exception as e:
        st.error(f"Error fetching documents: {e}")
        return []


def create_conversation(user_id: str, title: str, filter_values: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Create a new conversation"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/conversations/",
            json={
                "user_id": user_id,
                "title": title,
                "filter_values": filter_values or {}
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error creating conversation: {e}")
        return None


def get_conversations(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get conversations for a user"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/conversations/{user_id}", params={"limit": limit})
        response.raise_for_status()
        data = response.json()
        return data.get("conversations", [])
    except Exception as e:
        st.error(f"Error fetching conversations: {e}")
        return []


def get_conversation_messages(user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
    """Get messages for a conversation"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/conversations/{user_id}/{conversation_id}/messages")
        response.raise_for_status()
        data = response.json()
        return data.get("messages", [])
    except Exception as e:
        st.error(f"Error fetching messages: {e}")
        return []


def update_conversation_filters(user_id: str, conversation_id: str, filter_values: Dict[str, Any]) -> bool:
    """Update conversation filters"""
    try:
        response = requests.put(
            f"{API_BASE_URL}/api/conversations/{user_id}/{conversation_id}/filters",
            json={"filter_values": filter_values}
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error updating filters: {e}")
        return False


def send_chat_message(query: str, filters: Optional[Dict[str, Any]] = None, message_history: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
    """Send a chat message to the Talk To Contract agent"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chat/",
            json={
                "query": query,
                "filters": filters,
                "message_history": message_history or []
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error sending chat message: {e}")
        return None


def save_message_to_db(
    user_id: str,
    conversation_id: str,
    role: str,
    content: str,
    filter_values: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Save a message to DynamoDB via the conversation service"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/conversations/{user_id}/{conversation_id}/messages",
            json={
                "role": role,
                "content": content,
                "filter_values": filter_values,
                "metadata": metadata
            }
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Error saving message: {e}")
        return False


# Initialize Session State
def init_session_state():
    """Initialize session state variables"""
    if "user_id" not in st.session_state:
        st.session_state.user_id = DEFAULT_USER_ID

    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None

    if "selected_documents" not in st.session_state:
        st.session_state.selected_documents = []

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "conversation_filters" not in st.session_state:
        st.session_state.conversation_filters = {}


# UI Components
def render_sidebar():
    """Render the sidebar with document selection and conversation management"""
    with st.sidebar:
        st.title("🗂️ Document Selection")

        # Fetch documents
        documents = get_documents()

        if not documents:
            st.warning("No documents available. Please check the database connection.")
            return

        # Create document options for multiselect
        document_options = {
            f"{doc['document_title']} ({doc['contract_type']})": doc
            for doc in documents
        }

        # Determine default selection based on current conversation filters
        default_selections = []
        if st.session_state.conversation_filters.get("documents"):
            # Get document titles from current conversation
            current_doc_titles = {
                doc.get("document_title") for doc in st.session_state.conversation_filters.get("documents", [])
            }
            # Match them with available documents
            default_selections = [
                name for name, doc in document_options.items()
                if doc["document_title"] in current_doc_titles
            ]

        # Document multiselect
        selected_doc_names = st.multiselect(
            "Select documents to chat with:",
            options=list(document_options.keys()),
            default=default_selections,
            help="Select one or more documents to include in your conversation context"
        )

        # Update selected documents in session state
        st.session_state.selected_documents = [
            {
                "project_id": document_options[name]["project_id"],
                "reference_doc_id": document_options[name]["reference_doc_id"],
                "document_title": document_options[name]["document_title"]
            }
            for name in selected_doc_names
        ]

        # Display selected documents count
        st.info(f"📄 {len(st.session_state.selected_documents)} document(s) selected")

        st.divider()

        # Conversation Management
        st.title("💬 Conversations")

        # New conversation button
        if st.button("➕ New Conversation", use_container_width=True):
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            filter_values = {"documents": st.session_state.selected_documents} if st.session_state.selected_documents else {}

            conv = create_conversation(st.session_state.user_id, title, filter_values)
            if conv:
                st.session_state.current_conversation_id = conv["conversation_id"]
                st.session_state.messages = []
                st.session_state.conversation_filters = filter_values
                st.success(f"Created: {title}")
                st.rerun()

        # Load existing conversations
        conversations = get_conversations(st.session_state.user_id)

        if conversations:
            st.subheader("Recent Conversations")
            for conv in conversations[:10]:  # Show last 10 conversations
                conv_id = conv["conversation_id"]
                conv_title = conv["title"]
                doc_count = len(conv.get("filter_values", {}).get("documents", []))

                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        f"📋 {conv_title} ({doc_count} docs)",
                        key=f"conv_{conv_id}",
                        use_container_width=True
                    ):
                        st.session_state.current_conversation_id = conv_id
                        st.session_state.conversation_filters = conv.get("filter_values", {})

                        # Load conversation messages
                        messages = get_conversation_messages(st.session_state.user_id, conv_id)
                        st.session_state.messages = messages
                        st.rerun()

        st.divider()

        # Update filters button
        if st.session_state.current_conversation_id:
            if st.button("💾 Update Conversation Filters", use_container_width=True):
                # Calculate what changed
                current_docs = st.session_state.conversation_filters.get("documents", [])
                new_docs = st.session_state.selected_documents
                
                # Get document titles for comparison
                current_titles = {doc.get("document_title") for doc in current_docs}
                new_titles = {doc.get("document_title") for doc in new_docs}
                
                # Calculate added and removed
                added_titles = new_titles - current_titles
                removed_titles = current_titles - new_titles
                
                # Build activity message
                activity_parts = []
                if added_titles:
                    activity_parts.append(f"Added {len(added_titles)} file(s): {', '.join(added_titles)}")
                if removed_titles:
                    activity_parts.append(f"Removed {len(removed_titles)} file(s): {', '.join(removed_titles)}")
                
                if activity_parts:
                    activity_message = f"{' | '.join(activity_parts)}. Total {len(new_docs)} file(s) in global filter."
                else:
                    activity_message = f"No changes to document selection. Total {len(new_docs)} file(s) in global filter."
                
                # Update filters in backend
                filter_values = {"documents": new_docs} if new_docs else {}
                if update_conversation_filters(
                    st.session_state.user_id,
                    st.session_state.current_conversation_id,
                    filter_values
                ):
                    # Save activity as user message
                    save_message_to_db(
                        user_id=st.session_state.user_id,
                        conversation_id=st.session_state.current_conversation_id,
                        role="user",
                        content=activity_message,
                        filter_values=filter_values
                    )
                    
                    # Update session state
                    st.session_state.conversation_filters = filter_values
                    st.session_state.messages.append({
                        "role": "user",
                        "content": activity_message,
                        "created_at": datetime.now().isoformat()
                    })
                    
                    st.success("Filters updated!")
                    st.rerun()


def render_chat_interface():
    """Render the main chat interface"""
    # Display logo
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "contramate-logo-primary.svg")
    if os.path.exists(logo_path):
        st.image(logo_path, width=300)
    else:
        st.title("[Contra].[Mate]")  # Fallback if logo not found

    # Show current conversation info
    if st.session_state.current_conversation_id:
        documents = st.session_state.conversation_filters.get("documents", [])
        doc_count = len(documents)

        if doc_count > 0:
            # Create a formatted list of document titles
            doc_titles = [doc.get("document_title", "Unknown") for doc in documents]

            # Show count and expandable list
            with st.expander(f"📂 Active Conversation | {doc_count} document(s) in context", expanded=False):
                for idx, title in enumerate(doc_titles, 1):
                    st.markdown(f"{idx}. {title}")
        else:
            st.info(f"📂 Active Conversation | No documents selected")
    else:
        st.warning("⚠️ No active conversation. Create a new conversation to start chatting.")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show metadata (timestamp and response time for assistant messages)
            metadata_parts = []
            if "created_at" in message:
                metadata_parts.append(f"🕒 {message['created_at']}")
            if message["role"] == "assistant" and "response_time" in message:
                # Handle response_time as either string or float
                response_time = message['response_time']
                if response_time is not None:
                    if isinstance(response_time, str):
                        metadata_parts.append(f"⏱️ {response_time}s")
                    else:
                        metadata_parts.append(f"⏱️ {response_time:.2f}s")

            if metadata_parts:
                st.caption(" | ".join(metadata_parts))

    # Chat input
    if prompt := st.chat_input("Ask a question about the contracts..."):
        if not st.session_state.current_conversation_id:
            st.error("Please create or select a conversation first!")
            return

        # Add user message to chat
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare message history (OpenAI format)
        message_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in st.session_state.messages
        ]

        # Prepare filters
        filters = st.session_state.conversation_filters if st.session_state.conversation_filters.get("documents") else None

        # Send to API with timing
        start_time = time.time()
        with st.spinner("Thinking..."):
            response = send_chat_message(prompt, filters, message_history)
        elapsed_time = time.time() - start_time

        if response and response.get("success"):
            # Format answer with inline citations and references
            formatted_answer = format_answer_with_citations_markdown(response)

            # Display assistant response with formatted citations
            with st.chat_message("assistant"):
                st.markdown(formatted_answer)

                # Show response time
                st.caption(f"⏱️ Response time: {elapsed_time:.2f}s")

            # Save user message to DynamoDB
            save_message_to_db(
                user_id=st.session_state.user_id,
                conversation_id=st.session_state.current_conversation_id,
                role="user",
                content=prompt,
                filter_values=filters
            )

            # Save assistant response to DynamoDB with response time in metadata
            # Convert response_time to string to avoid DynamoDB float type issues
            save_message_to_db(
                user_id=st.session_state.user_id,
                conversation_id=st.session_state.current_conversation_id,
                role="assistant",
                content=formatted_answer,
                filter_values=filters,
                metadata={"response_time": f"{elapsed_time:.2f}"}
            )

            # Update session state messages for immediate display
            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "created_at": datetime.now().isoformat()
            })
            st.session_state.messages.append({
                "role": "assistant",
                "content": formatted_answer,
                "created_at": datetime.now().isoformat(),
                "response_time": elapsed_time  # Store response time
            })

            st.rerun()
        else:
            st.error(f"Error: {response.get('error', 'Unknown error')}" if response else "Failed to get response")


# Main App
def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Contramate - Contract Chat",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    init_session_state()

    # Render UI components
    render_sidebar()
    render_chat_interface()


if __name__ == "__main__":
    main()
