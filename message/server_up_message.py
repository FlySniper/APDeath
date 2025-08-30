import asyncio

import discord

from config.config import MESSAGE_CHANNEL


async def server_up_message(client: discord.Client, file):
    embed = discord.embeds.Embed()
    embed.title = "Server Up"
    embed.description = f"A new multiworld has been created"
    embed.color = 0x00FF00
    channel = client.get_channel(MESSAGE_CHANNEL)
    if channel is not None:
        await channel.send(file=discord.File(file), embed=embed)