from pydantic import BaseModel


class PromptRequest(BaseModel):
    prompt: str
    quality: int = 5

from typing import List
from pydantic import BaseModel


class Task(BaseModel):
    step: int
    agent: str
    task: str


class Plan(BaseModel):
    tasks: List[Task]