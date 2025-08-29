import asyncio

import discord

from config.config import MESSAGE_CHANNEL


async def death_message(client: discord.Client, death_count):
    embed = discord.embeds.Embed()
    embed.title = "Death"
    embed.description = f"Somebody died, creating a new multiworld. Deaths: {death_count}"
    embed.color = 0xFF0000
    channel = client.get_channel(MESSAGE_CHANNEL)
    if channel is not None:
        await channel.send(embed=embed)