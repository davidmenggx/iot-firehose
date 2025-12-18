from pydantic import BaseModel, Field

class DatabasePayload(BaseModel):
    """
    id: primary key, 8 byte bigint
    reading: 2 byte smallint
    """
    id: int
    reading: int = Field(ge=-32768, le=32767) # enforce smallint

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