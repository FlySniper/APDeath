import discord
from discord.interactions import Interaction

from client.APClient import set_client_running
from server.server import reroll


async def reroll_command(interaction: Interaction):
    await interaction.response.defer()
    embed = discord.embeds.Embed()
    embed.title = "Reroll"
    embed.description = f"Reroll without death caused by <@!{interaction.user.id}>"
    embed.color = 0xFF0000
    reroll(True)
    await interaction.followup.send(embed=embed)