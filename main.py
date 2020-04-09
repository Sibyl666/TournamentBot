import os
import discord
from discord.ext import commands

from database import read_tournament_db, write_tournament_db, get_settings
from registration_check import get_players_by_discord

settings = get_settings()

client = commands.Bot(command_prefix=settings['prefix'], case_insensitive=True)

cog_list = ["beatmaps", "paged_embeds", "misc", "lobbies", "qualifier_results"]

for cog in cog_list:
    client.load_extension(cog)


@client.event
async def on_ready():
    db = read_tournament_db()
    guild = client.get_guild(402213530599948299)
    player_role = discord.utils.get(guild.roles, id=693574523324203009)

    print(f"Checking player roles..")
    for member in guild.members:
        id = member.id
        if player_role in member.roles:
            player_found = False
            for team in db["teams"]:
                user1 = team["user1"]
                user2 = team["user2"]
                if (id == user1 or id == user2):
                    player_found = True

            if not player_found:
                print(f"Removing {player_role} role from {member}")
                await member.remove_roles(player_role)

        elif player_role not in member.roles:
            for team in db["teams"]:
                user1 = team["user1"]
                user2 = team["user2"]
                if (id == user1 or id == user2):
                    print(f"Adding {player_role} role to {member}")
                    await member.add_roles(player_role)

    print(f"Bot Started!!")
    return


client.run(os.environ["TOKEN"])

