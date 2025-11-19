"""
Database Schemas for Biology Learning App

Each Pydantic model maps to a MongoDB collection (lowercased class name).
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class Chapter(BaseModel):
    """
    Biology chapters with structured learning content.
    Collection: "chapter"
    """
    slug: str = Field(..., description="URL-friendly unique identifier, e.g., cell-structure")
    title: str = Field(..., description="Chapter title")
    summary: str = Field(..., description="Short overview in your own words")
    objectives: List[str] = Field(default_factory=list, description="Learning objectives")
    sections: List[dict] = Field(default_factory=list, description="List of content sections with heading and body")

class QuizQuestion(BaseModel):
    """
    Multiple choice questions associated with a chapter.
    Collection: "quizquestion"
    """
    chapter_slug: str = Field(..., description="Slug of the related chapter")
    question: str = Field(..., description="Question text")
    options: List[str] = Field(..., min_items=2, description="Answer choices")
    correct_index: int = Field(..., ge=0, description="Index into options for the correct answer")
    explanation: str = Field(..., description="Explanation for the correct answer")
    difficulty: str = Field("OSN-N", description="Difficulty label")
