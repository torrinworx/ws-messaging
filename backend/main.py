import sys
import asyncio
import websockets

async def connection(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")
        response_message = f"Echo: {message}"
        await websocket.send(response_message)
        print(f"Sent message: {response_message}")

async def connect_to_remote_server(uri):
    retry_backoff = 1  # Initial backoff time in seconds

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Connected to remote server at {uri}")
                while True:
                    await websocket.send("Test message from client")
                    response = await websocket.recv()
                    print(f"Client received: {response}")
                    await asyncio.sleep(5)  # Sending message every 5 seconds
        except ConnectionRefusedError:
            print(f"Connection to {uri} failed, retrying in {retry_backoff} seconds...")
            await asyncio.sleep(retry_backoff)
            retry_backoff = min(retry_backoff * 2, 60)  # Exponential backoff, max 60 seconds

async def server(port, remote_port):
    server_instance = await websockets.serve(connection, 'localhost', port)
    print(f"Server running on ws://localhost:{port}")

    uri = f"ws://localhost:{remote_port}"
    client_coroutine = connect_to_remote_server(uri)

    await asyncio.gather(server_instance.wait_closed(), client_coroutine)

    try:
        await server_instance.wait_closed()
    except asyncio.CancelledError:
        print("\nShutting Down...")
    finally:
        server_instance.close()
        await server_instance.wait_closed()
        print("Shutdown complete.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <port> <remote_port>")
        sys.exit(1)

    port = int(sys.argv[1])
    remote_port = int(sys.argv[2])
    try:
        asyncio.run(server(port, remote_port))
    except KeyboardInterrupt:
        print("WebSocket server interrupted and will be shut down.")
