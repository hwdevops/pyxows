from asyncio.tasks import sleep
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


async def task_client_1(ip, usr, pw, name):
    try:
        async with xows.XoWSClient(ip, username=usr, password=pw) as client:
            # wait for all connections to be up
            await asyncio.sleep(3)

            # callback interactions: callback is bound to client websocket connection
            async def callback(data, id_):
                logger.info(f'{name}: Feedback (Id {id_}): {data}')
                if id_ == 0:
                    client_1_status_systemunit_state = await client.xGet(['Status', 'SystemUnit', 'State'])
                    logger.debug(f"{name}: {client_1_status_systemunit_state}")

                    # place call on hold after client_2 accepted call
                    # INFO: Webex Board 55 Feedback(Id 0): {'Status': {'Call': [{'Status': 'Connected', 'id': 29}]}}
                    # INFO: Webex Board 55 Feedback(Id 1): {'Status': {'SystemUnit': {'State': {'NumberOfActiveCalls': 1, 'NumberOfInProgressCalls': 0}}}}
                    # DEBUG: {'NumberOfActiveCalls': 1, 'NumberOfInProgressCalls': 0, 'NumberOfSuspendedCalls': 0}
                    if client_1_status_systemunit_state['NumberOfActiveCalls'] == 1 and client_1_status_systemunit_state['NumberOfInProgressCalls'] == 0 and client_1_status_systemunit_state['NumberOfSuspendedCalls'] == 0:
                        if 'Status' in data['Status']['Call'][0].keys():
                            if data['Status']['Call'][0]['Status'] == 'Connected':
                                call_id_1 = data['Status']['Call'][0]['id']
                                await asyncio.sleep(3)
                                await client.xCommand(['Call', 'Hold'], Reason='Conference', CallId=call_id_1)

                    # call client_3 when call to client_2 is on hold
                    # INFO: Webex Board 55 Feedback(Id 0): {'Status': {'Call': [{'Status': 'OnHold', 'id': 29}]}}
                    # INFO: Webex Board 55 Feedback(Id 1): {'Status': {'SystemUnit': {'State': {'NumberOfActiveCalls': 0, 'NumberOfSuspendedCalls': 1}}}}
                    # DEBUG: {'NumberOfActiveCalls': 0, 'NumberOfInProgressCalls': 0, 'NumberOfSuspendedCalls': 1}
                    if client_1_status_systemunit_state['NumberOfActiveCalls'] == 1 and client_1_status_systemunit_state['NumberOfInProgressCalls'] == 0 and client_1_status_systemunit_state['NumberOfSuspendedCalls'] == 0:
                        if 'Status' in data['Status']['Call'][0].keys():
                            if data['Status']['Call'][0]['Status'] == 'Connected':
                                await asyncio.sleep(3)
                                await client.xCommand(['Dial'], Number='40035050000002@inte.vrvideo.de')

                    # join calls
                    # INFO: Webex Board 55 Feedback(Id 0): {'Status': {'Call': [{'Status': 'Connected', 'id': 31}]}}
                    # INFO: Webex Board 55 Feedback(Id 1): {'Status': {'SystemUnit': {'State': {'NumberOfActiveCalls': 1, 'NumberOfInProgressCalls': 0}}}}
                    # DEBUG: {'NumberOfActiveCalls': 1, 'NumberOfInProgressCalls': 0, 'NumberOfSuspendedCalls': 1}
                    if client_1_status_systemunit_state['NumberOfActiveCalls'] == 1 and client_1_status_systemunit_state['NumberOfInProgressCalls'] == 0 and client_1_status_systemunit_state['NumberOfSuspendedCalls'] == 1:
                        if 'Status' in data['Status']['Call'][0].keys():
                            if data['Status']['Call'][0]['Status'] == 'Connected':
                                await asyncio.sleep(3)
                                await client.xCommand(['Call', 'Join'])


            # Register Feedbacks
            # xFeedback ID 0
            logger.info(f"{name}: Subscription 0: {await client.subscribe(['Status', 'Call', 'Status'], callback)}")
            # xFeedback ID 1
            logger.info(f"{name}: Subscription 1: {await client.subscribe(['Status', 'SystemUnit', 'State'], callback)}")

            # fetch status from client
            client_1_status_sip = await client.xGet(['Status', 'SIP'])
            client_1_status_systemunit_state = await client.xGet(['Status', 'SystemUnit', 'State'])
            logger.info(f"{name}: Status: {client_1_status_sip}")
            logger.info(f"{name}: Status: {client_1_status_systemunit_state}")

            # store some status values and states
            client_1_sip_registered = True if client_1_status_sip['Registration'][0]['Status'] == 'Registered' else False
            client_1_NumberOfActiveCalls = client_1_status_systemunit_state['NumberOfActiveCalls']
            client_1_NumberOfInProgressCalls = client_1_status_systemunit_state['NumberOfInProgressCalls']
            client_1_NumberOfSuspendedCalls = client_1_status_systemunit_state['NumberOfSuspendedCalls']

            if client_1_sip_registered:
                # check call status of client
                if client_1_NumberOfActiveCalls == 0 and client_1_NumberOfInProgressCalls == 0 and client_1_NumberOfSuspendedCalls == 0:
                    # dial client_2
                    await client.xCommand(['Dial'], Number='40038010000005@inte.vrvideo.de')
                else:
                    logger.error(f"{name}: Device has a call: NumberOfActiveCalls: {client_1_NumberOfActiveCalls}, NumberOfInProgressCalls: {client_1_NumberOfInProgressCalls}, NumberOfSuspendedCalls: {client_1_NumberOfSuspendedCalls}")
                    await client.disconnect()
                    exit(0)
            else:
                logger.error(f"{name}: Device is not registered.")
                await client.disconnect()
                exit(0)

            await client.wait_until_closed()
    except Exception as e:
        logger.error(f"{name}: {e}")


async def task_client_2(ip, usr, pw, name):
    try:
        async with xows.XoWSClient(ip, username=usr, password=pw) as client:
            #xFeedback ID 0
            # wait for all connections to be up
            await asyncio.sleep(3)

            # callback interactions: callback is bound to client websocket connection
            async def callback(data, id_):
                logger.info(f'{name}: Feedback (Id {id_}): {data}')
                if id_ == 0:
                    client_2_status_systemunit_state = await client.xGet(['Status', 'SystemUnit', 'State'])
                    logger.debug(f"{name}: {client_2_status_systemunit_state}")
                    if client_2_status_systemunit_state['NumberOfActiveCalls'] == 0 and client_2_status_systemunit_state['NumberOfInProgressCalls'] == 1 and client_2_status_systemunit_state['NumberOfSuspendedCalls'] == 0:
                        # Room Kit Feedback (Id 0): {'Status': {'Call': [{'Status': 'Ringing', 'id': 9}]}}
                        if 'Status' in data['Status']['Call'][0].keys():
                            if data['Status']['Call'][0]['Status'] == 'Ringing':
                                await client.xCommand(['Call', 'Accept'])


            # Register Feedbacks
            # xFeedback ID 0
            logger.info(f"{name}: Subscription 0: {await client.subscribe(['Status', 'Call', 'Status'], callback)}")
            logger.info(f"{name}: Subscription 1: {await client.subscribe(['Status', 'SystemUnit', 'State'], callback)}")

            # fetch status from client
            client_2_status_sip = await client.xGet(['Status', 'SIP'])
            client_2_status_systemunit_state = await client.xGet(['Status', 'SystemUnit', 'State'])
            logger.info(f"{name}: Status: {client_2_status_sip}")
            logger.info(f"{name}: Status: {client_2_status_systemunit_state}")

            # store some status values and states
            client_2_sip_registered = True if client_2_status_sip['Registration'][0]['Status'] == 'Registered' else False
            client_2_NumberOfActiveCalls = client_2_status_systemunit_state['NumberOfActiveCalls']
            client_2_NumberOfInProgressCalls = client_2_status_systemunit_state['NumberOfInProgressCalls']
            client_2_NumberOfSuspendedCalls = client_2_status_systemunit_state['NumberOfSuspendedCalls']

            if client_2_sip_registered:
                pass
            else:
                logger.error(f"{name}: Device is not registered.")
                await client.disconnect()
                exit(0)

            await client.wait_until_closed()
    except Exception as e:
        logger.error(f"{name}: {e}")

async def task():
    codecs = [
        (env.ip_address_webex_board, env.ce_username, env.ce_password, 'Webex Board 55'),
        (env.ip_address_room_kit, env.ce_username, env.ce_password, 'Room Kit'),
        # (env.ip_address_dx80, env.ce_username, env.ce_password, 'DX80')
    ]

    coros = [
        task_client_1(*codecs[0]),
        task_client_2(*codecs[1])
    ]


    await asyncio.wait(coros)

if __name__ == "__main__":
    # create logger and time stamp
    logger, time_stamp = setup_custom_logger('websocket', __file__, 'debug')

    asyncio.run(task())

