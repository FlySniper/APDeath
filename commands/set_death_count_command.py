import discord
from discord.interactions import Interaction

from client.APClient import set_client_running
from server.server import reroll


async def set_death_count_command(interaction: Interaction, deaths: int):
    await interaction.response.defer()
    embed = discord.embeds.Embed()
    embed.title = "Set Death Count"
    embed.description = f"Death count set to {deaths}.\nCaused by <@!{interaction.user.id}>"
    embed.color = 0xFFFF00
    reroll(True)
    with open("death_count.txt", "w+") as death_file:
        death_file.write(str(deaths))
    await interaction.followup.send(embed=embed)