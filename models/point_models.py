from pydantic import BaseModel


class PointRequest(BaseModel):

    latitude: float

    longitude: float