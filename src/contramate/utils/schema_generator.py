"""
Utility to generate SQL schema documentation from SQLModel classes.

Extracts field names, types, and descriptions to create comprehensive
schema documentation for LLM prompts.
"""

from typing import Dict, List, Any, Type
from sqlmodel import SQLModel
from pydantic.fields import FieldInfo


def get_field_info(model_class: Type[SQLModel]) -> List[Dict[str, Any]]:
    """
    Extract field information from a SQLModel class.

    Args:
        model_class: SQLModel class to analyze

    Returns:
        List of dictionaries with field metadata

    Example:
        >>> fields = get_field_info(ContractAsmd)
        >>> for field in fields:
        ...     print(f"{field['name']}: {field['description']}")
    """
    fields = []

    for field_name, field_info in model_class.model_fields.items():
        # Get field annotation (type)
        field_type = field_info.annotation
        type_name = (
            field_type.__name__
            if hasattr(field_type, "__name__")
            else str(field_type)
        )

        # Get field description
        description = field_info.description or "No description"

        # Check if field is optional
        is_optional = field_info.is_required() is False

        # Get default value if exists
        default = None
        if field_info.default is not None:
            default = str(field_info.default)

        fields.append(
            {
                "name": field_name,
                "type": type_name,
                "description": description,
                "optional": is_optional,
                "default": default,
            }
        )

    return fields


def generate_schema_markdown(
    model_class: Type[SQLModel], include_optional: bool = True
) -> str:
    """
    Generate markdown documentation for a SQLModel schema.

    Args:
        model_class: SQLModel class to document
        include_optional: Whether to include optional fields

    Returns:
        Markdown formatted schema documentation

    Example:
        >>> schema_doc = generate_schema_markdown(ContractAsmd)
        >>> print(schema_doc)
    """
    fields = get_field_info(model_class)
    table_name = model_class.__tablename__

    # Build markdown
    lines = [
        f"## Table: {table_name}",
        "",
        "| Field Name | Type | Description | Required |",
        "|------------|------|-------------|----------|",
    ]

    for field in fields:
        if not include_optional and field["optional"]:
            continue

        required = "✅" if not field["optional"] else "❌"
        lines.append(
            f"| {field['name']} | {field['type']} | {field['description']} | {required} |"
        )

    return "\n".join(lines)


def generate_sql_schema_prompt(
    model_class: Type[SQLModel],
    include_optional: bool = True,
    max_text_length: int = 100,
) -> str:
    """
    Generate a concise schema description for LLM system prompts.

    Designed for SQL query generation agents.

    Args:
        model_class: SQLModel class to document
        include_optional: Whether to include optional fields
        max_text_length: Maximum description length (truncate if longer)

    Returns:
        Formatted schema description for system prompt

    Example:
        >>> prompt = generate_sql_schema_prompt(ContractAsmd)
        >>> print(prompt)
    """
    fields = get_field_info(model_class)
    table_name = model_class.__tablename__

    lines = [f"**Table: `{table_name}`**", ""]

    # Group fields by category based on naming patterns
    categories = {
        "Primary Keys": [],
        "Core Identifiers": [],
        "Document Metadata": [],
        "Parties & Dates": [],
        "Contract Clauses": [],
        "Financial Terms": [],
        "IP & Licensing": [],
        "Liability & Warranty": [],
        "Other Provisions": [],
        "Timestamps": [],
    }

    for field in fields:
        if not include_optional and field["optional"]:
            continue

        field_name = field["name"]
        description = field["description"]

        # Truncate long descriptions
        if len(description) > max_text_length:
            description = description[:max_text_length] + "..."

        field_line = f"  - `{field_name}` ({field['type']}): {description}"

        # Categorize field
        if "primary_key" in str(field.get("default", "")).lower():
            categories["Primary Keys"].append(field_line)
        elif field_name in ["project_id", "reference_doc_id"]:
            categories["Primary Keys"].append(field_line)
        elif field_name in ["document_title", "contract_type"]:
            categories["Core Identifiers"].append(field_line)
        elif "document_name" in field_name:
            categories["Document Metadata"].append(field_line)
        elif any(
            kw in field_name
            for kw in ["parties", "date", "agreement", "effective", "expiration"]
        ):
            categories["Parties & Dates"].append(field_line)
        elif any(
            kw in field_name
            for kw in [
                "compete",
                "exclusivity",
                "solicit",
                "disparagement",
                "termination",
                "rofr",
                "control",
                "assignment",
            ]
        ):
            categories["Contract Clauses"].append(field_line)
        elif any(
            kw in field_name
            for kw in ["revenue", "price", "commitment", "volume", "cost"]
        ):
            categories["Financial Terms"].append(field_line)
        elif any(kw in field_name for kw in ["ip", "license", "escrow"]):
            categories["IP & Licensing"].append(field_line)
        elif any(kw in field_name for kw in ["liability", "warranty", "damages"]):
            categories["Liability & Warranty"].append(field_line)
        elif any(
            kw in field_name
            for kw in [
                "insurance",
                "audit",
                "covenant",
                "beneficiary",
                "created",
                "updated",
            ]
        ):
            if "created" in field_name or "updated" in field_name:
                categories["Timestamps"].append(field_line)
            else:
                categories["Other Provisions"].append(field_line)
        else:
            categories["Other Provisions"].append(field_line)

    # Build prompt with non-empty categories
    for category, fields_list in categories.items():
        if fields_list:
            lines.append(f"**{category}:**")
            lines.extend(fields_list)
            lines.append("")

    return "\n".join(lines)


def generate_filter_field_list(model_class: Type[SQLModel]) -> List[str]:
    """
    Generate a list of fields suitable for WHERE clause filtering.

    Returns fields that are commonly used for filtering:
    - Primary keys
    - Indexed fields
    - Enum/categorical fields
    - Non-text fields

    Args:
        model_class: SQLModel class to analyze

    Returns:
        List of field names suitable for filtering

    Example:
        >>> filter_fields = generate_filter_field_list(ContractAsmd)
        >>> print(filter_fields)
        ['project_id', 'reference_doc_id', 'contract_type', ...]
    """
    fields = get_field_info(model_class)
    filter_fields = []

    for field in fields:
        field_name = field["name"]
        field_type = field["type"]

        # Include primary keys
        if field_name in ["project_id", "reference_doc_id"]:
            filter_fields.append(field_name)
        # Include contract_type
        elif field_name == "contract_type":
            filter_fields.append(field_name)
        # Include answer fields (they are short Yes/No values)
        elif field_name.endswith("_answer"):
            filter_fields.append(field_name)
        # Include dates
        elif "date" in field_name.lower():
            filter_fields.append(field_name)

    return filter_fields
