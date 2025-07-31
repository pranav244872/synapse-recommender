# app/schemas.py

from typing import List
from pydantic import BaseModel, Field

# --- Request Schemas ---

class RecommendationRequest(BaseModel):
    """
    Defines the expected input for the recommendation endpoint.
    """
    skill_ids: List[int] = Field(..., description="A list of skill IDs required for a task.")
    limit: int = Field(10, gt=0, le=50, description="The maximum number of recommendations to return.")


# --- Response Schemas ---

class Recommendation(BaseModel):
    """
    Represents a single recommended user.
    """
    user_id: int
    score: float = Field(..., description="The model's predicted score for this user-task fit.")


class RecommendationResponse(BaseModel):
    """
    Defines the structure of the data returned by the recommendation endpoint.
    """
    recommendations: List[Recommendation]
