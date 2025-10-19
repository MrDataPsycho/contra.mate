"""
Sample Project and Document IDs from bronze-v2 data.

This module provides real project IDs and document IDs for testing OpenSearch filters.
The data structure follows: data/bronze-v2/{project_id}/{internal_document_id}/
"""

# Sample Project IDs (from data/bronze-v2 directory)
SAMPLE_PROJECT_IDS = [
    "00149794-2432-4c18-b491-73d0fafd3efd",
    "008a9fd2-9a4a-4c3f-ad5c-d33eca94af3b",
    "0096b72f-1c0d-4724-924f-011f87d3591a",
    "00ab9a0d-4510-4833-bbdb-07abd9e49775",
    "00b8501a-19e1-4004-a1ef-76636d796c79",
]

# Sample Documents (project_id -> document_ids mapping)
SAMPLE_DOCUMENTS = {
    "00149794-2432-4c18-b491-73d0fafd3efd": [
        "577ff0a3-a032-5e23-bde3-0b6179e97949"
    ],
    "008a9fd2-9a4a-4c3f-ad5c-d33eca94af3b": [
        "aa1a0c65-8016-5d11-bbde-22055140660b"
    ],
    "0096b72f-1c0d-4724-924f-011f87d3591a": [
        "16b6078b-248c-5ed9-83ef-20ee0af49396"
    ],
    "00ab9a0d-4510-4833-bbdb-07abd9e49775": [
        "f8f43441-a1be-520b-87b7-14ca6f09b41d"
    ],
}

# Composite IDs (project_id-internal_document_id format used in OpenSearch)
SAMPLE_COMPOSITE_IDS = [
    "00149794-2432-4c18-b491-73d0fafd3efd-577ff0a3-a032-5e23-bde3-0b6179e97949",
    "008a9fd2-9a4a-4c3f-ad5c-d33eca94af3b-aa1a0c65-8016-5d11-bbde-22055140660b",
    "0096b72f-1c0d-4724-924f-011f87d3591a-16b6078b-248c-5ed9-83ef-20ee0af49396",
    "00ab9a0d-4510-4833-bbdb-07abd9e49775-f8f43441-a1be-520b-87b7-14ca6f09b41d",
]


def get_sample_project_id(index: int = 0) -> str:
    """
    Get a sample project ID.

    Args:
        index: Index of the project ID to retrieve (0-4)

    Returns:
        Project ID string
    """
    return SAMPLE_PROJECT_IDS[index % len(SAMPLE_PROJECT_IDS)]


def get_sample_document_id(project_id: str, index: int = 0) -> str:
    """
    Get a sample document ID for a given project.

    Args:
        project_id: The project ID
        index: Index of the document ID to retrieve

    Returns:
        Document ID string or None if project not found
    """
    docs = SAMPLE_DOCUMENTS.get(project_id, [])
    if not docs:
        return None
    return docs[index % len(docs)]


def get_sample_composite_id(index: int = 0) -> str:
    """
    Get a sample composite ID (project_id-document_id).

    Args:
        index: Index of the composite ID to retrieve

    Returns:
        Composite ID string
    """
    return SAMPLE_COMPOSITE_IDS[index % len(SAMPLE_COMPOSITE_IDS)]


def print_sample_data():
    """Print all sample data in a formatted way."""
    print("Sample Data from bronze-v2")
    print("=" * 80)

    for i, project_id in enumerate(SAMPLE_PROJECT_IDS, 1):
        print(f"\nProject {i}:")
        print(f"  ID: {project_id}")

        docs = SAMPLE_DOCUMENTS.get(project_id, [])
        for j, doc_id in enumerate(docs, 1):
            print(f"  Document {j}: {doc_id}")
            print(f"  Composite: {project_id}-{doc_id}")


if __name__ == "__main__":
    print_sample_data()
