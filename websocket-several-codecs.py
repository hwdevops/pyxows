import env
import xows
import asyncio

import logging
import os
import sys
from datetime import datetime, timezone


def setup_custom_logger(logger_name, file_name, level_name=None, stream_handler=True, file_handler=True):
    """
    setup custom logger

    Parameters:
        logger_name (str): use built-in variable __name__ which evaluates to the name of the current module
        file_name (str): use __file__ which evaluates to the pathname of the file from which the module was loaded
        level_name (str): logging level (debug, info, warning, error, critical)


    Returns:
        logger (obj): logger object
        time_stamp (str): time stamp in ISO format

    Example:
        logger, time_stamp = helper.setup_custom_logger(__name__, __file__, 'info')
    """

    LEVELS = {'debug': logging.DEBUG,
              'info': logging.INFO,
              'warning': logging.WARNING,
              'error': logging.ERROR,
              'critical': logging.CRITICAL}

    level = LEVELS.get(str(level_name).lower(), logging.NOTSET)

    time_stamp = create_timestamp_iso().replace(':', '-')

    # file_path = os.getcwd()
    script_file_name = os.path.basename(file_name)
    log_file_name = (f'{time_stamp}_{script_file_name}.log')
    open(log_file_name, 'w').close()    # touch file

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    log_formatter = logging.Formatter(
        '%(asctime)s : %(filename)-22s : %(levelname)-8s : %(message)s')
    log_stream_handler = logging.StreamHandler(sys.stdout)
    log_stream_handler.setFormatter(log_formatter)
    if stream_handler:
        logger.addHandler(log_stream_handler)
    log_file_handler = logging.FileHandler(log_file_name, encoding="UTF-8")
    log_file_handler.setFormatter(log_formatter)
    if file_handler:
        logger.addHandler(log_file_handler)

    return logger, time_stamp


def create_timestamp_iso():
    """
    Create ISO timestamp

    Parameter:

    Returns:
        time_stamp (str): ISO formated time stamp
    """

    local_time = datetime.now(timezone.utc).astimezone()
    time_stamp = local_time.isoformat()

    return time_stamp


async def start(ip, usr, pw, name):
    try:
        async with xows.XoWSClient(ip, username=usr, password=pw) as client:
            async def callback(data, id_):
                logger.info(f'{name} Feedback (Id {id_}): {data}')
                if id_ == 0:
                    if data['Status']['Audio']['Volume'] > 60:
                        await client.xCommand(['Audio', 'Volume', 'Set'], Level=60)

            logger.info(f"{name} Status Query: {await client.xQuery(['Status', '**', 'DisplayName'])}")
            logger.info(f"{name} Get: {await client.xGet(['Status', 'Audio', 'Volume'])}")
            logger.info(f"{name} Command: {await client.xCommand(['Audio', 'Volume', 'Set'], Level=60)}")
            logger.info(f"{name} Configuration: {await client.xSet(['Configuration', 'Audio', 'DefaultVolume'], 50)}")
            logger.info(f"{name} Subscription 0: {await client.subscribe(['Status', 'Audio', 'Volume'], callback, True)}")
            logger.info(f"{name} Subscription 1: {await client.subscribe(['Status', 'Audio', 'Microphones', 'Mute'], callback, True)}")

            await client.wait_until_closed()
    except Exception as e:
        logger.error(e)

async def task():
    codecs = [(env.ip_address_webex_board, env.ce_username, env.ce_password, 'Webex Board 55'),
                (env.ip_address_room_kit, env.ce_username, env.ce_password, 'Room Kit'),
                (env.ip_address_dx80, env.ce_username, env.ce_password, 'DX80'),]
    connections = [start(*codec) for codec in codecs]

    await asyncio.wait(connections)

if __name__ == "__main__":
    # create logger and time stamp
    logger, time_stamp = setup_custom_logger('websocket', __file__, 'info')

    asyncio.run(task())

