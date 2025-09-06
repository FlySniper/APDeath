import asyncio
import os.path
import random
import re
import shutil
import subprocess
import zipfile
import atexit
from os import PathLike

import pexpect
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from time import sleep

from typing_extensions import LiteralString

from client.APClient import run_client, set_client_running
from config.config import AP_BASE_YAML_LOCATION, AP_INSTALL_LOCATION, FREE_LOCATIONS_PER_DEATH, PORT
from message.death_message import death_message
from message.server_up_message import server_up_message

REROLL = False
DEATH = False

async def async_sleep(seconds):
    await asyncio.to_thread(sleep, seconds)

def reroll(reroll):
    global REROLL
    set_client_running(not reroll)
    REROLL = reroll


def read_death_count():
    if not os.path.isfile("death_count.txt"):
        return 0
    with open("death_count.txt", "r") as death_file:
        file_contents = death_file.read()
        return int(file_contents)

def remove_output_files():
    output_dir = os.path.join(AP_INSTALL_LOCATION, "output")
    if os.path.isdir(output_dir):
        for (dirpath, dirnames, filenames) in os.walk(output_dir):
            for filename in filenames:
                os.remove(os.path.join(output_dir, filename))
            break

def copy_yamls():
    players_dir = os.path.join(AP_INSTALL_LOCATION, "Players")
    for (dirpath, dirnames, filenames) in os.walk(players_dir):
        for filename in filenames:
            os.remove(os.path.join(players_dir, filename))
        break
    [shutil.copy(os.path.join(AP_BASE_YAML_LOCATION, filename), players_dir) 
     for filename in os.listdir(AP_BASE_YAML_LOCATION)]


async def ap_generate():
    file_extension = ""
    if os.name == "nt":
        file_extension = ".exe"
    def generate_call():
        ap_generate_file = os.path.join(AP_INSTALL_LOCATION, "ArchipelagoGenerate" + file_extension)
        subprocess.call((ap_generate_file,))
    await asyncio.to_thread(generate_call)

def ap_check_game_in_progress():
    output_dir = os.path.join(AP_INSTALL_LOCATION, "output")
    if os.path.isdir(output_dir):
        for (dirpath, dirnames, filenames) in os.walk(output_dir):
            for filename in filenames:
                return True
            return False
            break

async def ap_server(death_count, client):
    global REROLL
    global DEATH
    REROLL = False
    file_extension = ""
    if os.name == "nt":
        file_extension = ".exe"

    output_dir = os.path.join(AP_INSTALL_LOCATION, "output")
    artifacts_file = os.path.join(AP_INSTALL_LOCATION, "output", "artifacts.zip")
    output_file = find_output_file(output_dir)

    if output_file == "":
        copy_yamls()
        remove_output_files()
        await ap_generate()

    ap_spoiler_log = find_spoiler_artifacts(artifacts_file, output_dir, output_file)
    ap_server_file = os.path.join(AP_INSTALL_LOCATION, "ArchipelagoServer" + file_extension)
    p = pexpect.spawn(f"bash -c \"{ap_server_file} --host 0.0.0.0 --port {PORT} --hint_cost 10 {output_file}\"",
                      encoding="utf-8")
    atexit.register(p.close)
    locations_slots = get_locations_from_spoiler(ap_spoiler_log)
    await asyncio.to_thread(p.expect, **{"pattern": "server listening on", "timeout": 30000})
    if DEATH:
        for i in range(0, death_count * FREE_LOCATIONS_PER_DEATH):
            if i > len(locations_slots) - 1:
                break
            index = random.randint(0, len(locations_slots) - 1)
            location_slot = locations_slots[index]
            locations_slots.pop(index)
            p.sendline(f"/send_location {location_slot[1]} {location_slot[0]}\n")
            p.flush()
    await server_up_message(client, artifacts_file)
    await run_client()
    await async_sleep(5)
    p.close(True)
    if not p.closed:
        quit(-1)
    DEATH = True
    if not REROLL:
        print("Death detected. Restarting.")
        await death_message(client, death_count + 1)
        with open("death_count.txt", "w+") as death_file:
            death_file.write(str(death_count + 1))


def find_spoiler_artifacts(artifacts_file, output_dir, output_file):
    ap_spoiler_log = ""
    if os.path.exists(artifacts_file):
        os.remove(artifacts_file)
    ap_output_file = zipfile.ZipFile(output_file)
    artifacts = zipfile.ZipFile(artifacts_file, "a")
    for file in ap_output_file.namelist():
        if file.endswith(".txt"):
            ap_output_file.extract(file, output_dir)
            ap_spoiler_log = os.path.join(output_dir, file)
        elif file != "artifacts.zip":
            ap_output_file.extract(file, output_dir)
            artifacts.write(os.path.join(output_dir, file), file)
    artifacts.close()
    return ap_spoiler_log


def find_output_file(output_dir):
    output_file= ""
    for (dirpath, dirnames, filenames) in os.walk(output_dir):
        for filename in filenames:
            filename: str = filename
            if filename.endswith(".zip") and filename != "artifacts.zip":
                output_file = os.path.join(output_dir, filename)
    return output_file


def get_locations_from_spoiler(ap_spoiler_log):
    locations_slots = []
    with open(ap_spoiler_log, "r") as spoiler:
        line = spoiler.readline()
        while line is not None:
            if line.startswith("Locations:"):
                break
            line = spoiler.readline()
        line = spoiler.readline()
        while line is not None:
            if line.startswith("Playthrough:"):
                break
            if not line.startswith("\r") and not line.startswith("\n"):
                colon_split = line.split("):")
                if len(colon_split) == 0:
                    location_name = location_name_slot
                    slot_name = "Player1"
                else:
                    location_name_slot = colon_split[0]
                    location_name_slot = location_name_slot + ")"
                    match_list = re.findall("\\([^\\(\\)]*\\)$", location_name_slot)
                    if len(match_list) > 0:
                        slot_name_paren = match_list[-1]
                        location_name = location_name_slot[:(len(slot_name_paren) + 1)*-1]
                        slot_name = slot_name_paren[1:-1]
                    else:
                        location_name = location_name_slot
                        slot_name = "Player1"
                locations_slots.append((location_name, slot_name))
            line = spoiler.readline()
    return locations_slots


async def server_monitor(client):
    while True:
        death_count = read_death_count()
        if not ap_check_game_in_progress():
            copy_yamls()
            await ap_generate()
        await ap_server(death_count, client)
        copy_yamls()
        remove_output_files()
        await ap_generate()