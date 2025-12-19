from typing import Annotated, Optional
from datetime import datetime, timezone

from pydantic import BaseModel, Field, AfterValidator

def enforce_smallint(value: int) -> int:
    if not (-32768 <= value <= 32767):
        raise ValueError('Reading must be a 2 byte signed integer')
    return value

SmallInt = Annotated[int, AfterValidator(enforce_smallint)] # used to enforce reading value is of type smallint to match postgres database

class DatabasePayload(BaseModel):
    """
    id: primary key, 8 byte bigint
    reading: 2 byte smallint
    timestamp: timestamp with time zone
    """
    id: int
    reading: SmallInt
    # Important: database posts should not specify timestamp except for debugging purposes
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc)) # use default factory to generate datetime at time of request

class ResponseModel(BaseModel):
    """
    To be returned after posting reading
    """
    status: str
    message: str
    timestamp: datetime

successful_response = ResponseModel(
        status='success',
        message='Item created',
        timestamp=datetime.now(timezone.utc)
    )