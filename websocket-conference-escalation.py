"""
This script sets up a P2P video connection between two participants. After the P2P connection is established the call is escalated to an ad-hoc conference with three participants. Client_1 amd client_2 are monitoring the call status with xfeedback mechanism.

- client_1 calls client_2
- client_2 accepts the call
- at this point client_1 and client_2 have a P2P video call
- client_1 puts call to client_2 on hold
- client_1 calls client_3 (auto answer, recording server)
- client_3 accepts the call from client_1
- at this point client_1 amd client_3 have a P2P video call, and client_1 has one video call on hold
- client_1 escalates both video calls to an ad-hoc meeting by joining the two video calls
- after a specified duration all video calls are terminated

"""

from asyncio.tasks import sleep
import env
import xows
import asyncio

import logging
import os
import sys
import time
from datetime import datetime, timezone

call_duration = 120 # call duration in seconds

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


async def task_client_1(ip, usr, pw, name, disconnect_event):
    """
    Coroutine to:
    - set up websoket connection to Cisco CE codec
    - register xfeedbacks with callback
    - get status information from codec
    - dial client_2 if this codec is registered
    - place video call on hold when connected
    - dial client_3 if this codec is registered
    - escalated calls to an ad-hoc confernece by joining the two calls
    - wait for disconnect_event
    - disconnect call
    - close websocket connection
    """

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
                    # INFO: Room Kit Mini: Feedback (Id 0): {'Status': {'Call': [{'Status': 'Connected', 'id': 23}]}}
                    # INFO: Room Kit Mini: Feedback (Id 1): {'Status': {'SystemUnit': {'State': {'NumberOfActiveCalls': 1, 'NumberOfInProgressCalls': 0}}}}
                    # DEBUG: Room Kit Mini: {'NumberOfActiveCalls': 1, 'NumberOfInProgressCalls': 0, 'NumberOfSuspendedCalls': 0}
                    if client_1_status_systemunit_state['NumberOfActiveCalls'] == 1 and client_1_status_systemunit_state['NumberOfInProgressCalls'] == 0 and client_1_status_systemunit_state['NumberOfSuspendedCalls'] == 0 and not disconnect_event.is_set():
                        if 'Status' in data['Status']['Call'][0].keys():
                            if data['Status']['Call'][0]['Status'] == 'Connected':
                                call_id_1 = data['Status']['Call'][0]['id']
                                await asyncio.sleep(3)
                                logger.info(f'{name}: placing call on hold...')
                                await client.xCommand(['Call', 'Hold'], Reason='Conference', CallId=call_id_1)

                    # call client_3 when call to client_2 is on hold
                    # INFO: Room Kit Mini: Feedback (Id 0): {'Status': {'Call': [{'Status': 'OnHold', 'id': 23}]}}
                    # INFO: Room Kit Mini: Feedback(Id 1): {'Status': {'SystemUnit': {'State': {'NumberOfActiveCalls': 0, 'NumberOfSuspendedCalls': 1}}}}
                    # DEBUG: Room Kit Mini: {'NumberOfActiveCalls': 0, 'NumberOfInProgressCalls': 0, 'NumberOfSuspendedCalls': 1}
                    #! Prüfen: 'NumberOfSuspendedCalls': 1
                    if client_1_status_systemunit_state['NumberOfActiveCalls'] == 0 and client_1_status_systemunit_state['NumberOfInProgressCalls'] == 0 and client_1_status_systemunit_state['NumberOfSuspendedCalls'] == 1 and not disconnect_event.is_set():
                        if 'Status' in data['Status']['Call'][0].keys():
                            if data['Status']['Call'][0]['Status'] == 'OnHold':
                                await asyncio.sleep(3)
                                # client_3_sip_address = env.sip_address_webex_board
                                client_3_sip_address = env.sip_address_recorder
                                logger.info(f"{name}: dialing '{client_3_sip_address}'...")
                                #! IMPORTANT: client have to have auto answer enabled!
                                await client.xCommand(['Dial'], Number=client_3_sip_address)

                    # join calls
                    # INFO: Room Kit Mini: Feedback(Id 0): {'Status': {'Call': [{'Status': 'Connected', 'id': 24}]}}
                    # INFO: Room Kit Mini: Feedback(Id 1): {'Status': {'SystemUnit': {'State': {'NumberOfActiveCalls': 1, 'NumberOfInProgressCalls': 0}}}}
                    # DEBUG: Room Kit Mini: {'NumberOfActiveCalls': 1, 'NumberOfInProgressCalls': 0, 'NumberOfSuspendedCalls': 1}
                    if client_1_status_systemunit_state['NumberOfActiveCalls'] == 1 and client_1_status_systemunit_state['NumberOfInProgressCalls'] == 0 and client_1_status_systemunit_state['NumberOfSuspendedCalls'] == 1 and not disconnect_event.is_set():
                        if 'Status' in data['Status']['Call'][0].keys():
                            if data['Status']['Call'][0]['Status'] == 'Connected':
                                await asyncio.sleep(15) # wait for some seconds before joing the call and getting a recording of the P2P call from client_1 to the
                                logger.info(f"{name}: joining calls...")
                                await client.xCommand(['Call', 'Join'])

                                # wait for disconnect_event to become True; is set by timer() function
                                await wait_for(disconnect_event)

                                # (optional) sleep for some seconds before disconnecting the call
                                await asyncio.sleep(1)

                                logger.info(f'{name}: disconneting call!')
                                await client.xCommand(['Call', 'Disconnect'])

                                # set some paramters
                                # xcommand Audio Volume Set Level: 1
                                await client.xCommand(['Audio', 'Volume', 'Set'], Level=50)
                                # xconfiguration Video Input Connector 2 Quality: Sharpness
                                # xconfiguration Video Input Connector[2] Quality: Sharpness
                                await client.xSet(['Configuration', 'Video', 'Input', 'Connector[2]', 'Quality'], 'Sharpness')
                                # configure Camera as MainVideoSource
                                # xcommand Video Input SetMainVideoSource SourceId: 1
                                await client.xCommand(['Video', 'Input', 'SetMainVideoSource'], SourceId=1)

                                # (optional) sleep for 2 seconds to fetch feedback messages before closing client webesocket connection
                                await asyncio.sleep(2)
                                logger.info(f'{name}: disconneting client websocket connection!')
                                await client.disconnect()

                    if 'CameraLid' in client_1_status_systemunit_state and client_1_status_systemunit_state['CameraLid'] != 'Open':
                        logger.warning(f'{name}: camera lid has been closed!')


            # fetch status from client
            client_1_status_sip = await client.xGet(['Status', 'SIP'])
            client_1_status_systemunit_state = await client.xGet(['Status', 'SystemUnit', 'State'])
            logger.info(f"{name}: Status: {client_1_status_sip}")
            logger.info(f"{name}: Status: {client_1_status_systemunit_state}")

            # store some status values and states
            client_1_sip_registered = True if client_1_status_sip['Registration'][0]['Status'] == 'Registered' else False
            if 'CameraLid' not in client_1_status_systemunit_state:
                # in this case codec does not have a camera lid, thus you can not lose it and it is open all time
                client_1_camera_lid_open = True
            else:
                client_1_camera_lid_open = True if client_1_status_systemunit_state['CameraLid'] == 'Open' else False
            client_1_NumberOfActiveCalls = client_1_status_systemunit_state['NumberOfActiveCalls']
            client_1_NumberOfInProgressCalls = client_1_status_systemunit_state['NumberOfInProgressCalls']
            client_1_NumberOfSuspendedCalls = client_1_status_systemunit_state['NumberOfSuspendedCalls']

            if not disconnect_event.is_set():
                if client_1_sip_registered:
                    # check call status of client
                    if client_1_camera_lid_open and not disconnect_event.is_set():
                        # Register Feedbacks
                        # xFeedback ID 0
                        logger.info(f"{name}: Subscription 0: {await client.subscribe(['Status', 'Call', 'Status'], callback)}")
                        # xFeedback ID 1
                        logger.info(f"{name}: Subscription 1: {await client.subscribe(['Status', 'SystemUnit', 'State'], callback)}")

                        # set some paramters
                        # xcommand Audio Volume Set Level: 1
                        await client.xCommand(['Audio', 'Volume', 'Set'], Level=1)
                        # xconfiguration Video Input Connector 2 PreferredResolution: 1920_1080_60
                        # xconfiguration Video Input Connector[2] PreferredResolution: 1920_1080_60
                        await client.xSet(['Configuration', 'Video', 'Input', 'Connector[2]', 'PreferredResolution'], '1920_1080_60')
                        # xconfiguration Video Input Connector 2 Quality: Motion
                        # xconfiguration Video Input Connector[2] Quality: Motion
                        await client.xSet(['Configuration', 'Video', 'Input', 'Connector[2]', 'Quality'], 'Motion')
                        # configure HDMI player as MainVideoSource
                        # xcommand Video Input SetMainVideoSource SourceId: 2
                        await client.xCommand(['Video', 'Input', 'SetMainVideoSource'], SourceId=2)

                        # INFO: Room Kit Mini: Status: {'NumberOfActiveCalls': 0, 'NumberOfInProgressCalls': 0, 'NumberOfSuspendedCalls': 0}
                        if client_1_NumberOfActiveCalls == 0 and client_1_NumberOfInProgressCalls == 0 and client_1_NumberOfSuspendedCalls == 0 and not disconnect_event.is_set():
                            # dial client_2
                            client_2_sip_address = env.sip_address_room_kit
                            logger.info(f"{name}: dialing '{client_2_sip_address}'...")
                            await client.xCommand(['Dial'], Number=client_2_sip_address)
                        else:
                            logger.error(f"{name}: Device has a call: NumberOfActiveCalls: {client_1_NumberOfActiveCalls}, NumberOfInProgressCalls: {client_1_NumberOfInProgressCalls}, NumberOfSuspendedCalls: {client_1_NumberOfSuspendedCalls}")
                            await client.disconnect()
                            return disconnect_event.set()
                    else:
                        logger.error(f"{name}: Device's camera lid is closed! Aborting ...")
                        await client.disconnect()
                        return disconnect_event.set()
                else:
                    logger.error(f"{name}: Device is not registered! Aborting ...")
                    await client.disconnect()
                    return disconnect_event.set()
            else:
                logger.error(f"{name}: Disconnect Event is set! Aborting ...")
                await client.disconnect()
                return disconnect_event.set()

            await client.wait_until_closed()
    except Exception as e:
        logger.error(f"{name}: {e}")
        return disconnect_event.set()


async def task_client_2(ip, usr, pw, name, disconnect_event):
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
                    # INFO: Room Kit: Feedback (Id 1): {'Status': {'SystemUnit': {'State': {'NumberOfInProgressCalls': 1}}}}
                    if client_2_status_systemunit_state['NumberOfActiveCalls'] == 0 and client_2_status_systemunit_state['NumberOfInProgressCalls'] == 1 and client_2_status_systemunit_state['NumberOfSuspendedCalls'] == 0 and not disconnect_event.is_set():
                        # INFO: Room Kit: Feedback (Id 0): {'Status': {'Call': [{'Status': 'Ringing', 'id': 59}]}}
                        if 'Status' in data['Status']['Call'][0].keys():
                            if data['Status']['Call'][0]['Status'] == 'Ringing':
                                logger.info(f'{name}: accepting incoming call...')
                                await client.xCommand(['Call', 'Accept'])

                                # wait for disconnect_event
                                await wait_for(disconnect_event)

                                # (optional) sleep for some seconds before disconnecting the call
                                await asyncio.sleep(1)

                                logger.info(f'{name}: disconneting call!')
                                await client.xCommand(['Call', 'Disconnect'])

                                # set some paramters
                                # xcommand Audio Volume Set Level: 1
                                await client.xCommand(['Audio', 'Volume', 'Set'], Level=50)
                                # xconfiguration Video Input Connector 2 Quality: Sharpness
                                # xconfiguration Video Input Connector[2] Quality: Sharpness
                                await client.xSet(['Configuration', 'Video', 'Input', 'Connector[2]', 'Quality'], 'Sharpness')
                                # configure Camera as MainVideoSource
                                # xcommand Video Input SetMainVideoSource SourceId: 1
                                await client.xCommand(['Video', 'Input', 'SetMainVideoSource'], SourceId=1)

                                # (optional) sleep for 2 seconds to fetch feedback messages before closing client webesocket connection
                                await asyncio.sleep(2)
                                logger.info(
                                    f'{name}: disconneting client websocket connection!')
                                await client.disconnect()

            # fetch status from client
            client_2_status_sip = await client.xGet(['Status', 'SIP'])
            client_2_status_systemunit_state = await client.xGet(['Status', 'SystemUnit', 'State'])
            logger.info(f"{name}: Status: {client_2_status_sip}")
            logger.info(f"{name}: Status: {client_2_status_systemunit_state}")

            # store some status values and states
            client_2_sip_registered = True if client_2_status_sip['Registration'][0]['Status'] == 'Registered' else False
            if 'CameraLid' not in client_2_status_systemunit_state:
                # in this case codec does not have a camera lid, thus you can not lose it and it is open all time
                client_2_camera_lid_open = True
            else:
                client_2_camera_lid_open = True if client_2_status_systemunit_state['CameraLid'] == 'Open' else False
            client_2_NumberOfActiveCalls = client_2_status_systemunit_state['NumberOfActiveCalls']
            client_2_NumberOfInProgressCalls = client_2_status_systemunit_state['NumberOfInProgressCalls']
            client_2_NumberOfSuspendedCalls = client_2_status_systemunit_state['NumberOfSuspendedCalls']

            if not disconnect_event.is_set():
                if client_2_sip_registered:
                    if client_2_camera_lid_open:
                        # Register Feedbacks
                        # xFeedback ID 0
                        logger.info(f"{name}: Subscription 0: {await client.subscribe(['Status', 'Call', 'Status'], callback)}")
                        logger.info(f"{name}: Subscription 1: {await client.subscribe(['Status', 'SystemUnit', 'State'], callback)}")

                        # set some paramters
                        # xcommand Audio Volume Set Level: 1
                        await client.xCommand(['Audio', 'Volume', 'Set'], Level=1)
                        # xconfiguration Video Input Connector 2 PreferredResolution: 1920_1080_60
                        # xconfiguration Video Input Connector[2] PreferredResolution: 1920_1080_60
                        await client.xSet(['Configuration', 'Video', 'Input', 'Connector[2]', 'PreferredResolution'], '1920_1080_60')
                        # xconfiguration Video Input Connector 2 Quality: Motion
                        # xconfiguration Video Input Connector[2] Quality: Motion
                        await client.xSet(['Configuration', 'Video', 'Input', 'Connector[2]', 'Quality'], 'Motion')
                        # configure HDMI player as MainVideoSource
                        # xcommand Video Input SetMainVideoSource SourceId: 2
                        await client.xCommand(['Video', 'Input', 'SetMainVideoSource'], SourceId=2)

                    else:
                        logger.error(f"{name}: Device's camera lid is closed! Aborting ...")
                        await client.disconnect()
                        return disconnect_event.set()
                else:
                    logger.error(f"{name}: Device is not registered! Aborting ...")
                    await client.disconnect()
                    return disconnect_event.set()
            else:
                logger.error(f"{name}: Disconnect Event is set! Aborting ...")
                await client.disconnect()
                return disconnect_event.set()

            await client.wait_until_closed()
    except Exception as e:
        logger.error(f"{name}: {e}")
        return disconnect_event.set()


async def wait_for(event):
    """
    This corouting can be used as a nested coroutine .
    Wait until the event is set.

    Parameters:
        event (asyncio event object)
    """
    logger.debug(f'{wait_for.__qualname__}: waiting for event ...')
    await event.wait()
    logger.debug(f'{wait_for.__qualname__}: ... got event!')


async def timer(event, duration):
    """
    This coroutine sets an event status to True after a specified duration

    Parameters:
        event (asyncio event object)
        duration (int)  duration in seconds
    """

    time_start = time.time()

    logger.debug(f'{timer.__qualname__}: waiting for timer ...')
    # event can be set from outside, thus check it is NOT set
    while time.time() < time_start + duration and not event.is_set():
        await asyncio.sleep(1)
    logger.debug(f'{timer.__qualname__}: setting event to True!')
    event.set()
    logger.debug(f'{timer.__qualname__}: ... timer end')


async def main():
    # Create an Event object.
    # https://docs.python.org/3/library/asyncio-sync.html#asyncio.Event
    # An event object. Not thread-safe.
    # An asyncio event can be used to notify multiple asyncio tasks that some event has happened.
    # An Event object manages an internal flag that can be set to true with the set() method and reset to false with the clear() method. The wait() method blocks until the flag is set to true. The flag is set to false initially.
    disconnect_event = asyncio.Event()

    # define list of coroutines that should be waited for
    coros = [
        asyncio.create_task(timer(disconnect_event, call_duration)),
        asyncio.create_task(task_client_1(env.ip_address_room_kit_mini_flip, env.ce_username, env.ce_password, 'Room Kit Mini', disconnect_event)),
        asyncio.create_task(task_client_2(env.ip_address_room_kit, env.ce_username, env.ce_password, 'Room Kit', disconnect_event))
    ]

    # wait for coroutines to be completed
    await asyncio.wait(coros)


if __name__ == "__main__":
    # create logger and time stamp
    logger, time_stamp = setup_custom_logger('websocket', __file__, 'debug')

    # Try using asyncio.get_event_loop().run_until_complete(main()) instead of asyncio.run(main())
    # https://stackoverflow.com/questions/65682221/runtimeerror-exception-ignored-in-function-proactorbasepipetransport
    asyncio.get_event_loop().run_until_complete(main())

