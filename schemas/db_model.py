from typing import Annotated
from datetime import datetime

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
    """
    id: int
    reading: SmallInt

class ResponseModel(BaseModel):
    """
    To be returned after posting reading
    """
    status: str
    message: str

successful_response = ResponseModel(
        status='success',
        message='Item created'
    )