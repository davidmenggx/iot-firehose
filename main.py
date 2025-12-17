import os
import asyncio
import logging

from fastapi import FastAPI
from pydantic import BaseModel
import redis
import asyncpg
from dotenv import load_dotenv

from redis_config import redis_client

load_dotenv()

app = FastAPI()

class DatabasePayload(BaseModel):
    """
    id: primary key, 8 byte bigint
    reading: 2 byte smallint
    """
    id: int
    reading: int

@app.post("/readings")
async def post_reading(reading: DatabasePayload):
    """
    Push client request to worker queue, return success
    """
    pass