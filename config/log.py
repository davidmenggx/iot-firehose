import logging

def setup_logger(VERBOSE: bool = False, CLEAR_LOG: bool = False) -> logging.Logger:
    """
    Set VERBOSE flag in config to visualize execution trace
    """
    logger = logging.getLogger('iot-firehose-logger')
    LOG_LEVEL = logging.DEBUG if VERBOSE else logging.INFO
    logging.basicConfig(filename='debug.log', encoding='utf-8', level=LOG_LEVEL) # creates the logger

    if CLEAR_LOG:
        with open('debug.log', 'w') as file: # clears the debug log
            pass
    
    return logger
