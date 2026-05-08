"""Search schemas for the API."""

from pydantic import BaseModel


class SearchQuery(BaseModel):
    """Schema for search queries.

    Attributes:
        query (str): The search term.
    """

    query: str
