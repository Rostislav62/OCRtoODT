from pydantic import BaseModel

class LineAnnotation(BaseModel):
    page: int
    line_no: int
    text: str
    cls: str  # TITLE, etc.
    bbox: list[float]
    centered: bool
    ends_with_hyphen: bool