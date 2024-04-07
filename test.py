import asyncio
import websockets
import ssl

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def test_server(uri):
    async with websockets.connect(uri, ssl=ssl_context) as websocket:
        await websocket.send("Health check")
        response = await websocket.recv()
        print(response)

asyncio.get_event_loop().run_until_complete(test_server('wss://localhost:4800'))
