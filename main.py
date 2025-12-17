#import os
import asyncio
import logging # figure this out too

# see if i can clean this up
from fastapi import FastAPI
#from pydantic import BaseModel
#import redis
#from rq import Queue
#import asyncpg
#from dotenv import load_dotenv

from schemas.db_model import DatabasePayload
from redis_config import task_queue
from app.workers import save_to_db

#load_dotenv()

app = FastAPI()

@app.post("/readings")
async def post_reading(reading: DatabasePayload):
    """
    Push client request to worker queue, return success
    """
    task_queue.enqueue(save_to_db, reading)
    # return some success code