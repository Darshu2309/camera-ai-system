from pydantic import BaseModel
from typing import Optional


class ParsedCommand(BaseModel):

    action: str

    camera_id: Optional[int] = None

    direction: Optional[str] = None

    angle: Optional[float] = None

    zoom: Optional[float] = None

    zoom_direction: Optional[str] = None

    continuous: bool = False

    target: Optional[str] = None