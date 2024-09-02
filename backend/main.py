import asyncio
import websockets
import sys

async def server(websocket, path):
    async for message in websocket:
        print(f"Message: {message}")
        await websocket.send(message)

async def main(port):
    start_server = await websockets.serve(server, 'localhost', port)
    print(f"WebSocket server started on ws://localhost:{port}")

    try:
        await start_server.wait_closed()
    except asyncio.CancelledError:
        print("Server is closing...")
    finally:
        start_server.close()
        await start_server.wait_closed()
        print("Server has been closed.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])

    try:
        asyncio.run(main(port))
    except KeyboardInterrupt:
        print("WebSocket server interrupted and will be shut down.")
