"""Product search schemas."""
from typing import List
from pydantic import BaseModel, Field


class ProductSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query in Arabic, Franco-Arabic, or English")
    limit: int = Field(default=3, ge=1, le=20, description="Maximum number of products to return")


class ProductInfo(BaseModel):
    id: str
    name: str
    price: float
    sizes: List[str]
    colors: List[str]
    stock_count: int
    description: str


class SearchMetadata(BaseModel):
    detected_language: str
    matched_keywords: List[str]
    total_found: int


class ProductSearchResponse(BaseModel):
    products: List[ProductInfo]
    formatted_for_ai: str
    search_metadata: SearchMetadata
