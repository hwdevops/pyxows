"""
await client.subscribe(['Status', 'Call', 'Status'], callback)

./python.exe websocket-example.py
<aiohttp.client.ClientSession object at 0x0000026DF819DB80>
Webex Board Status Query:  {'DeveloperPreview': {'Mode': 'Off'}, 'Hardware': {'HasWifi': 'True', 'Module': {'CompatibilityLevel': '0', 'SerialNumber': 'WZS2248E03C'}, 'Monitoring': {'Temperature': {'Status': 'Normal'}}}, 'ProductId': 'Cisco Webex Board 55S', 'ProductPlatform': 'Board 55S', 'ProductType': 'Cisco Codec', 'Software': {'DisplayName': 'RoomOS 10.3.3.0 e383f779e98', 'Name': 's53200', 'OptionKeys': {'Encryption': 'True', 'MultiSite': 'False', 'RemoteMonitoring': 'False'}, 'ReleaseDate': '2021-06-09', 'Version': 'ce10.3.3.0.e383f779e98'}, 'State': {'NumberOfActiveCalls': 0, 'NumberOfInProgressCalls': 0, 'NumberOfSuspendedCalls': 0}, 'Uptime': 85890}
Webex Board Feedback (Id 0): {'Status': {'Call': [{'Status': 'Dialling', 'id': 3}]}}
Webex Board Feedback (Id 0): {'Status': {'Call': [{'Status': 'Connecting', 'id': 3}]}}
Webex Board Feedback (Id 0): {'Status': {'Call': [{'Status': 'Connected', 'id': 3}]}}
Webex Board Feedback (Id 0): {'Status': {'Call': [{'Status': 'Disconnecting', 'id': 3}]}}
Webex Board Feedback (Id 0): {'Status': {'Call': [{'Status': 'Idle', 'id': 3}]}}
Webex Board Feedback (Id 0): {'Status': {'Call': [{'ghost': 'True', 'id': 3}]}}
"""

import xows
import asyncio

import env

async def start(ip, usr, pw, name):
    async with xows.XoWSClient(ip, username=usr, password=pw) as client:
        print(client._session)
        print(name + ' Status Query: ', await client.xGet(['Status', 'SystemUnit']))

        async def callback(data, id_):
            print(name + f' Feedback (Id {id_}): {data}')

        # await client.subscribe(['Event', '**'], callback)
        await client.subscribe(['Event', 'UserInterface', 'Extensions', 'Panel', 'Clicked'], callback)
        await client.subscribe(['Status', 'Call', 'Status'], callback)
        await client.wait_until_closed()

async def task():
    await start(env.ip_address_webex_board, env.ce_username, env.ce_password, 'Webex Board')

asyncio.run(task())
