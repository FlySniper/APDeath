import asyncio

import discord
from discord import app_commands
from discord.ext import tasks

from commands.death_command import death_command
from commands.get_death_count_command import get_death_count_command
from commands.reroll_command import reroll_command
from commands.set_death_count_command import set_death_count_command
from config.config import DISCORD_BOT_TOKEN
from server.server import server_monitor

COMMAND_GUILD_IDS = [706545364249083906, 723702183417348197]
class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())

    async def setup_hook(self) -> None:
        self.ap_monitor_task.start()

    @tasks.loop(seconds=1, count=1)
    async def ap_monitor_task(self):
        await server_monitor(self)
        quit(-2)

    @ap_monitor_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()

    async def on_ready(self):
        print("Logged on as {0}!".format(self.user))
        slash_command = app_commands.CommandTree(client)
        command = discord.app_commands.Command(name="death",
                                               description="Send a death and generate a new multiworld.",
                                               callback=death_command,
                                               guild_ids=COMMAND_GUILD_IDS)
        command.guild_only = True
        slash_command.add_command(command)
        command = discord.app_commands.Command(name="reroll",
                                               description="Send a reroll without a death and generate a new multiworld.",
                                               callback=reroll_command,
                                               guild_ids=COMMAND_GUILD_IDS)
        command.guild_only = True
        slash_command.add_command(command)
        command = discord.app_commands.Command(name="set_death_count",
                                               description="Sets the death count and rerolls the multiworld.",
                                               callback=set_death_count_command,
                                               guild_ids=COMMAND_GUILD_IDS)
        command.guild_only = True
        slash_command.add_command(command)
        command = discord.app_commands.Command(name="get_death_count",
                                               description="Gets the death count.",
                                               callback=get_death_count_command,
                                               guild_ids=COMMAND_GUILD_IDS)
        command.guild_only = True
        slash_command.add_command(command)
        for guild in COMMAND_GUILD_IDS:
            print(await slash_command.sync(guild=discord.Object(id=guild)))

client = MyClient()
client.run(DISCORD_BOT_TOKEN)