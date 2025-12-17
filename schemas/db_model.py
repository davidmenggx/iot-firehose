from pydantic import BaseModel

class DatabasePayload(BaseModel):
    """
    id: primary key, 8 byte bigint
    reading: 2 byte smallint
    """
    id: int
    reading: int