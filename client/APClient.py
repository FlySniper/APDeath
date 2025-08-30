import asyncio
import websockets
import json

from uuid import uuid4

CLIENT_RUNNING = False

def set_client_running(client_running):
    global CLIENT_RUNNING
    CLIENT_RUNNING = client_running

async def run_client():
    global CLIENT_RUNNING
    CLIENT_RUNNING = True
    async with websockets.connect("ws://127.0.0.1:6472") as websocket:
        while CLIENT_RUNNING:
            room_info = await websocket.recv()
            while CLIENT_RUNNING:
                await websocket.send(connect_cmd())
                connect_resp = await websocket.recv()
                connect_resp_json = json.loads(connect_resp)
                if connect_resp_json[0]["cmd"] == "Connected":
                    break
            await websocket.send(bounce_cmd())
            bounced_resp = await websocket.recv()
            while CLIENT_RUNNING:
                try:
                    server_resp = await asyncio.wait_for(websocket.recv(), timeout=5)
                    server_resp_json = json.loads(server_resp)
                    if server_resp_json[0]["cmd"] == "Bounced" and "DeathLink" in server_resp_json[0]["tags"]:
                        return
                except asyncio.TimeoutError:
                    pass


def bounce_cmd():
    bounce_str = json.dumps([{
        "cmd": "Bounce",
        "tags": ["DeathLink"]
                 }])
    return bounce_str

def connect_cmd():
    connect_str = json.dumps([{
        "cmd": "Connect",
        "password": "",
        "game": "Archipelago",
        "name": "Spectator",
        "uuid": str(uuid4()),
        "version": {"major": 0, "minor": 6, "build": 3, "class": "Version"},
        "items_handling": 0b000,
        "tags": ["DeathLink", "NoText"],
        "slot_data": False
                 }])
    return connect_str