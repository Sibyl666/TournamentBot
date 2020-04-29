import os
import discord
from discord.ext import commands

from database import read_tournament_db, get_settings, read_qualifier_results_db

settings = get_settings()

client = commands.Bot(command_prefix=settings['prefix'], case_insensitive=True)

cog_list = ["beatmaps", "paged_embeds", "misc", "lobbies", "qualifier_results", "matches"]

for cog in cog_list:
    client.load_extension(cog)


@client.event
async def on_ready():
    teams_db = read_tournament_db()
    teams_not_eliminated = ["Team Big Chungus", "SARS-CoV-3", "ali vefa fanclub", "isim bulamadık", "nE",
                            "NEŞESİNE YAŞAM", "1.yiz kasmayın", "kms", "i may be stupid", ".`**HIDDEN**`.", "Zurna",
                            "bucocukamerikalı"]
    guild = client.get_guild(402213530599948299)
    player_role = discord.utils.get(guild.roles, id=693574523324203009)

    qualified_players = []
    for team in teams_not_eliminated:
        for _team in teams_db["teams"]:
            if _team["name"] == team:
                qualified_players.append(_team["user1"])
                qualified_players.append(_team["user2"])

    for member in guild.members:
        if player_role in member.roles:
            if member.id not in qualified_players:
                print(f"Removing role from: {member}")
                await member.remove_roles(player_role)
        else:
            if member.id in qualified_players:
                print(f"Giving role to: {member}")
                await member.add_roles(player_role)

    print(f"Bot started!")
    return


client.run(os.environ["TOKEN"])
