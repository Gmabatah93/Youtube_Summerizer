import re

def _format_collection_name(name: str) -> str:
    """Format string to valid Qdrant collection name using regex."""
    # Replace spaces and special chars with underscore
    formatted = re.sub(r'[^a-zA-Z0-9]', '_', name)
    # Replace multiple underscores with single underscore
    formatted = re.sub(r'_+', '_', formatted)
    # Remove leading/trailing underscores
    formatted = formatted.strip('_')
    # Convert to lowercase for consistency
    formatted = formatted.lower()
    # Ensure name starts with letter (Qdrant requirement)
    if not formatted[0].isalpha():
        formatted = 'collection_' + formatted
    return formatted