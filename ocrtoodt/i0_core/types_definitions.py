# Путь: ocrtoodt/i0_core/types_definitions.py
from pydantic import BaseModel

class LineAnnotation(BaseModel):
    page: int
    line_no: int
    text: str
    bbox: list[float]
