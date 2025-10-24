"""
Utility functions for Streamlit UI.

Contains helper functions for formatting chat responses, citations, and references.
"""

import re
from typing import Dict, Tuple, Optional, Any


def format_answer_with_citations(
    response: Dict[str, Any]
) -> Tuple[str, Optional[str]]:
    """
    Format chat response answer with inline citations and reference list.

    This function:
    1. Replaces inline citation markers [doc1], [doc2], etc. with superscript numbers
    2. Creates a numbered reference list at the bottom

    Args:
        response: Chat API response containing:
            - answer: Text with inline citation markers like [doc1], [doc2]
            - citations: Dict mapping doc keys to document names
            - success: Boolean indicating success
            - error: Optional error message

    Returns:
        Tuple of (formatted_answer, references_text)
        - formatted_answer: Answer with [doc1] replaced by superscript numbers
        - references_text: Numbered list of references, or None if no citations

    Example:
        Input:
        {
            "answer": "Payment is due in 60 days [doc1]. Late fees apply [doc2].",
            "citations": {
                "doc1": "contract_v1.pdf",
                "doc2": "terms_conditions.pdf"
            }
        }

        Output:
        (
            "Payment is due in 60 days ¹. Late fees apply ².",
            "**References:**\n1. contract_v1.pdf\n2. terms_conditions.pdf"
        )
    """

    # Check for error or missing data
    if not response.get("success", False):
        error_msg = response.get("error", "Unknown error")
        return f"❌ Error: {error_msg}", None

    answer = response.get("answer", "")
    citations = response.get("citations", {})

    # If no citations, return answer as-is
    if not citations:
        return answer, None

    # Create mapping from doc keys to citation numbers
    # Sort by doc key to ensure consistent numbering (doc1, doc2, doc3, etc.)
    doc_keys = sorted(citations.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)

    doc_to_number = {doc_key: idx + 1 for idx, doc_key in enumerate(doc_keys)}

    # Superscript numbers (Unicode)
    superscript_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
    }

    def to_superscript(num: int) -> str:
        """Convert number to superscript string"""
        return ''.join(superscript_map[digit] for digit in str(num))

    # Replace inline citation markers with superscript numbers
    formatted_answer = answer
    for doc_key in doc_keys:
        citation_number = doc_to_number[doc_key]
        superscript_num = to_superscript(citation_number)

        # Replace [doc1], [doc2], etc. with superscript numbers
        pattern = re.escape(f"[{doc_key}]")
        formatted_answer = re.sub(pattern, superscript_num, formatted_answer)

    # Build references list
    references_lines = ["**References:**"]
    for doc_key in doc_keys:
        citation_number = doc_to_number[doc_key]
        document_name = citations[doc_key]
        references_lines.append(f"{citation_number}. {document_name}")

    references_text = "\n".join(references_lines)

    return formatted_answer, references_text


def format_answer_with_citations_markdown(
    response: Dict[str, Any]
) -> str:
    """
    Format chat response as complete markdown with answer and references.

    Args:
        response: Chat API response

    Returns:
        Markdown-formatted string with answer and references section

    Example output:
        '''
        Payment is due in 60 days ¹. Late fees apply ².

        ---

        **References:**
        1. contract_v1.pdf
        2. terms_conditions.pdf
        '''
    """
    formatted_answer, references = format_answer_with_citations(response)

    if references:
        return f"{formatted_answer}\n\n---\n\n{references}"
    else:
        return formatted_answer


def extract_citations_list(response: Dict[str, Any]) -> Optional[list]:
    """
    Extract citations as a simple list for display.

    Args:
        response: Chat API response

    Returns:
        List of document names, or None if no citations

    Example:
        ["contract_v1.pdf", "terms_conditions.pdf"]
    """
    citations = response.get("citations", {})
    if not citations:
        return None

    # Sort by doc key for consistent ordering
    doc_keys = sorted(citations.keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    return [citations[key] for key in doc_keys]


# Example usage
if __name__ == "__main__":
    # Test with example response
    test_response = {
        "success": True,
        "answer": "Payment terms include staged payments [doc1]. Interest applies to late payments [doc2]. Use fees are billed monthly [doc1].",
        "citations": {
            "doc1": "HEALTHGATEDATACORP_11_24_1999-EX-10.1-HOSTING AND MANAGEMENT AGREEMENT (1).pdf.md-2",
            "doc2": "contract_terms.pdf"
        },
        "metadata": {
            "filters_applied": True,
            "message_history_used": True
        },
        "error": None
    }

    formatted, refs = format_answer_with_citations(test_response)
    print("Formatted Answer:")
    print(formatted)
    print("\n" + refs)
    print("\n" + "="*50 + "\n")
    print("Full Markdown:")
    print(format_answer_with_citations_markdown(test_response))
