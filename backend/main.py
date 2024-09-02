import os
import asyncio
import websockets

async def connection(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")
        response_message = f"Echo: {message}"
        await websocket.send(response_message)
        print(f"Sent message: {response_message}")

async def server(port):
    server_instance = await websockets.serve(connection, 'localhost', port)
    print(f"Server running on ws://localhost:{port}")

    await asyncio.gather(server_instance.wait_closed())

    try:
        await server_instance.wait_closed()
    except asyncio.CancelledError:
        print("\nShutting Down...")
    finally:
        server_instance.close()
        await server_instance.wait_closed()
        print("Shutdown complete.")

if __name__ == "__main__":
    port = os.getenv("port", 5000)

    try:
        asyncio.run(server(port))
    except KeyboardInterrupt:
        print("WebSocket server interrupted and will be shut down.")
