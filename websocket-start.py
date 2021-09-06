"""
https://community.cisco.com/t5/collaboration-voice-and-video/xapi-over-websocket-xows-ce9-7-x/ba-p/3831553
"""

import websockets
import ssl
import asyncio
import base64

import env

async def connect():
    return await websockets.connect('wss://{}/ws/'.format(env.ip_address_webex_board), ssl=ssl._create_unverified_context(), extra_headers={
        'Authorization': 'Basic {}'.format(base64.b64encode('{}:{}'.format(env.ce_username, env.ce_password).encode()).decode('utf-8'))})

async def send(ws, message):
    await ws.send(message)
    print('Sending:', message)

async def receive(ws):
    result = await ws.recv()
    print('Receive:', result)

async def task():
    ws = await connect()
    try:
        await send(ws, '{"jsonrpc": "2.0","id": "0","method": "xGet","params": {"Path": ["Status", "SystemUnit", "State"]}}')
        await receive(ws)
    finally:
        ws.close()

asyncio.run(task())