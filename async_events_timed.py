import asyncio
import time


async def waiter(event):
    print(f'{waiter.__qualname__}: waiting for it ...')
    await event.wait()
    print(f'{waiter.__qualname__}: ... got it!')


async def timer(event):
    duration = 10   # [seconds]
    time_start = time.time()

    print(f'{timer.__qualname__}: waiting for timer ...')
    while time.time() < time_start + duration:
        await asyncio.sleep(1)
    event.set()


async def main():
    # Create an Event object.
    # https://docs.python.org/3/library/asyncio-sync.html#asyncio.Event
    event = asyncio.Event()

    # Spawn a Task to wait until 'event' is set.
    waiter_task = asyncio.create_task(waiter(event))
    asyncio.create_task(timer(event))

    # Wait until the waiter task is finished.
    await waiter_task

asyncio.run(main())