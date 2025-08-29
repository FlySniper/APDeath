import discord
from discord.interactions import Interaction

from client.APClient import set_client_running


async def death_command(interaction: Interaction):
    await interaction.response.defer()
    embed = discord.embeds.Embed()
    embed.title = "Manual Death"
    embed.description = f"Death caused by <@!{interaction.user.id}>"
    embed.color = 0xFF0000
    set_client_running(False)
    await interaction.followup.send(embed=embed)