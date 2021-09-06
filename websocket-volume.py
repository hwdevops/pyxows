import xows
import asyncio

import env

async def start(ip, usr, pw, name):
    async with xows.XoWSClient(ip, username=usr, password=pw) as client:
        async def callback(data, id_):
            print(name + f' Feedback (Id {id_}): {data}')
            if id_ == 0:
                if data['Status']['Audio']['Volume'] > 60:
                    await client.xCommand(['Audio', 'Volume', 'Set'], Level=60)

        print(name + ' Status Query:',
            await client.xQuery(['Status', '**', 'DisplayName']))

        print(name + ' Get:',
            await client.xGet(['Status', 'Audio', 'Volume']))

        print(name + ' Command:',
              await client.xCommand(['Audio', 'Volume', 'Set'], Level=60))

        print(name + ' Configuration:',
            await client.xSet(['Configuration', 'Audio', 'DefaultVolume'], 50))

        print(name + ' Subscription 0:',
            await client.subscribe(['Status', 'Audio', 'Volume'], callback, True))

        print(name + ' Subscription 1:',
              await client.subscribe(['Status', 'Audio', 'Microphones', 'Mute'], callback, True))

        await client.wait_until_closed()

async def task():
    codecs = [(env.ip_adderess_webex_board, env.ce_username, env.ce_password, 'Webex Board')]
    connections = [start(*codec) for codec in codecs]

    await asyncio.wait(connections)

asyncio.run(task())