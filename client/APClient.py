import asyncio
import logging
import random

import websockets
import json
import ssl

from uuid import uuid4

from websockets import WebSocketException

from config.config import PORT, FREE_LOCATIONS_PER_DEATH, OPENSSL, HOST_NAME
from message.server_up_message import server_up_message


CLIENT_RUNNING = False

logger = logging.getLogger(__name__)
def set_client_running(client_running):
    global CLIENT_RUNNING
    CLIENT_RUNNING = client_running

async def run_client(client, artifacts_file, server_process, send_free_locations, death_count):
    global CLIENT_RUNNING
    CLIENT_RUNNING = True
    if OPENSSL:
        address = f"wss://{HOST_NAME}:{PORT}"
    else:
        address = f"ws://127.0.0.1:{PORT}"
    async with websockets.connect(address, max_size=2**24) as websocket:
        while CLIENT_RUNNING:
            try:
                room_info = await websocket.recv()
                while CLIENT_RUNNING:
                    await websocket.send(connect_cmd("Spectator"))
                    connect_resp = await websocket.recv()
                    connect_resp_json = json.loads(connect_resp)
                    if connect_resp_json[0]["cmd"] == "Connected":
                        if send_free_locations:
                            location_slots_ids = []
                            for player in connect_resp_json[0]["players"]:
                                async with websockets.connect(address, max_size=2**24) as slot_socket:
                                    room_info_player = await slot_socket.recv()
                                    await slot_socket.send(connect_cmd(player["name"]))
                                    connect_player_resp = await slot_socket.recv()
                                    connect_player_resp_json = json.loads(connect_player_resp)
                                    if connect_player_resp_json[0]["cmd"] == "Connected":
                                        for location_id in connect_player_resp_json[0]["missing_locations"]:
                                            location_slots_ids.append((player["name"], location_id))

                            for i in range(0, death_count * FREE_LOCATIONS_PER_DEATH):
                                if i > len(location_slots_ids) - 1:
                                    break
                                index = random.randint(0, len(location_slots_ids) - 1)
                                location_slot = location_slots_ids[index]
                                location_slots_ids.pop(index)
                                server_process.sendline(f"/send_location {location_slot[0]} {location_slot[1]}\n")
                                server_process.flush()
                                logger.info(f"Sent location {location_slot[0]} {location_slot[1]}")
                        break
                await websocket.send(bounce_cmd())
                bounced_resp = await websocket.recv()
                await server_up_message(client, artifacts_file)
                while CLIENT_RUNNING:
                    try:
                        server_resp = await asyncio.wait_for(websocket.recv(), timeout=5)
                        server_resp_json = json.loads(server_resp)
                        if server_resp_json[0]["cmd"] == "Bounced" and "tags" in server_resp_json[0] and "DeathLink" in server_resp_json[0]["tags"]:
                            logger.info("Websocket closed: Death Link")
                            return
                    except asyncio.TimeoutError:
                        pass
                logger.info("Client Terminated")
            except WebSocketException as we:
                logger.error(f"Websocket Exception {we}")
                await websocket.close()


def bounce_cmd():
    bounce_str = json.dumps([{
        "cmd": "Bounce",
        "tags": ["DeathLink"]
                 }])
    return bounce_str

def connect_cmd(slot_name):
    connect_str = json.dumps([{
        "cmd": "Connect",
        "password": "",
        "game": None,
        "name": slot_name,
        "uuid": str(uuid4()),
        "version": {"major": 0, "minor": 6, "build": 3, "class": "Version"},
        "items_handling": 0b000,
        "tags": ["AP", "DeathLink", "NoText", "Tracker"],
        "slot_data": False
                 }])
    return connect_str

def get_data_package_cmd():
    get_data_package_str = json.dumps([{"cmd": "GetDataPackage"}])
    return get_data_package_str

def location_scouts_cmd(location_ids):
    location_scouts_str = json.dumps([{
        "cmd": "LocationScouts",
        "locations": location_ids,
        "create_as_hint": 0
    }])
    return location_scouts_str