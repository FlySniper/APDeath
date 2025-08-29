import discord
from discord.interactions import Interaction

from client.APClient import set_client_running
from config.config import FREE_LOCATIONS_PER_DEATH
from server.server import reroll, read_death_count


async def get_death_count_command(interaction: Interaction):
    await interaction.response.defer()
    deaths = read_death_count()
    embed = discord.embeds.Embed()
    embed.title = "Get Death Count"
    embed.description = f"There are currently {deaths} deaths and {deaths * FREE_LOCATIONS_PER_DEATH} total free locations."
    embed.color = 0x00FF00
    await interaction.followup.send(embed=embed)