#!/bin/bash
# Script to run Streamlit UI for Contramate

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Error: streamlit is not installed"
    echo "Please run: uv sync --group ui"
    exit 1
fi

# Run streamlit app
echo "Starting Contramate Streamlit UI..."
echo "Access the UI at: http://localhost:8501"
echo ""

streamlit run src/contramate/ui/app.py
