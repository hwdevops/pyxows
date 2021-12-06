"""
Use asyncio and websocket to connect to a Cisco CE Code, dial into a conference and disconnect after a speficied duration (wait time).
"""

import time
import xows
import asyncio

import env


async def client_websocket_connection(ip, usr, pw, name, event):
    """
    Coroutine to:
    - set up websoket connection to Cisco CE codec
    - get status information from codec
    - dial into conference if codec is registered
    - wait for event
    - disconnect call
    - close websocket connection
    """

    async with xows.XoWSClient(ip, username=usr, password=pw) as client:
        print(name + ' Status Query: ', await client.xGet(['Status', 'SystemUnit']))


        async def callback(data, id_):
            print(f'{name}: Feedback (Id {id_}): {data}')


        # (optional) register feedback, here only to see call status
        # xFeedback ID 0
        await client.subscribe(['Status', 'Call', 'Status'], callback)

        # fetch status from client
        client_status_sip = await client.xGet(['Status', 'SIP'])
        client_status_systemunit_state = await client.xGet(['Status', 'SystemUnit', 'State'])
        print(f"{name}: Status: {client_status_sip}")
        print(f"{name}: Status: {client_status_systemunit_state}")

        # store some status values and states
        client_sip_registered = True if client_status_sip['Registration'][0]['Status'] == 'Registered' else False
        client_NumberOfActiveCalls = client_status_systemunit_state['NumberOfActiveCalls']
        client_NumberOfInProgressCalls = client_status_systemunit_state['NumberOfInProgressCalls']
        client_NumberOfSuspendedCalls = client_status_systemunit_state['NumberOfSuspendedCalls']

        if client_sip_registered:
            # check call status of client
            if client_NumberOfActiveCalls == 0 and client_NumberOfInProgressCalls == 0 and client_NumberOfSuspendedCalls == 0:
                # dial client_2
                await client.xCommand(['Dial'], Number='82999@vrvideo.de')

                # wait for event
                await waiter(event)

                # (optional) sleep for some seconds before disconnecting the call
                await asyncio.sleep(1)

                print(f'{name}: disconneting call!')
                await client.xCommand(['Call', 'Disconnect'])

                # (optional) sleep for 2 seconds to fetch feedback messages before closing client webesocket connection
                await asyncio.sleep(2)
                print(f'{name}: disconneting client websocket connection!')
                await client.disconnect()

            else:
                print(f"{name}: Device has a call: NumberOfActiveCalls: {client_NumberOfActiveCalls}, NumberOfInProgressCalls: {client_NumberOfInProgressCalls}, NumberOfSuspendedCalls: {client_NumberOfSuspendedCalls}")
                await client.disconnect()
                return event.set()

        else:
            print(f"{name}: Device is not registered.")
            await client.disconnect()
            return event.set()



async def waiter(event):
    """
    This corouting can be used as a nested coroutine .
    Wait until the event is set.

    Parameters:
        event (asyncio event object)
    """
    print(f'{waiter.__qualname__}: waiting for event ...')
    await event.wait()
    print(f'{waiter.__qualname__}: ... got event!')


async def timer(event):
    """
    This coroutine sets an event status to True after a specified duration

    Parameters:
        event (asyncio event object)
    """
    duration = 30   # [seconds]
    time_start = time.time()

    print(f'{timer.__qualname__}: waiting for timer ...')
    # event can be set from outside, thus check it is NOT set
    while time.time() < time_start + duration and not event.is_set():
        await asyncio.sleep(1)
    print(f'{timer.__qualname__}: setting event to True!')
    event.set()
    print(f'{timer.__qualname__}: ... timer end')


async def main():
    # Create an Event object.
    # https://docs.python.org/3/library/asyncio-sync.html#asyncio.Event
    stop_event = asyncio.Event()

    # define list of coroutines that should be waited for
    coros = [
        asyncio.create_task(timer(stop_event)),
        asyncio.create_task(client_websocket_connection(env.ip_address_webex_board, env.ce_username, env.ce_password, 'Webex Board', stop_event))
    ]

    # wait for coroutines to be completed
    await asyncio.wait(coros)

    print('THE END')

if __name__ == "__main__":
    # Try using asyncio.get_event_loop().run_until_complete(main()) instead of asyncio.run(main())
    # https://stackoverflow.com/questions/65682221/runtimeerror-exception-ignored-in-function-proactorbasepipetransport
    asyncio.get_event_loop().run_until_complete(main())
