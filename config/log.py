import logging
import os

from dotenv import load_dotenv

def setup_logger(VERBOSE: bool = False, CLEAR_LOG: bool = False) -> logging.Logger:
    logger = logging.getLogger('iot-firehose-logger')
    LOG_LEVEL = logging.DEBUG if VERBOSE else logging.INFO
    logging.basicConfig(filename='debug.log', encoding='utf-8', level=LOG_LEVEL)

    if CLEAR_LOG:
        with open('debug.log', 'w') as file: # clears the debug log
            pass
    
    return logger
