import os
import discord
from discord.ext import commands

from database import read_tournament_db, write_tournament_db, get_settings
from registration_check import get_players_by_discord

settings = get_settings()

client = commands.Bot(command_prefix=settings['prefix'], case_insensitive=True)

cog_list = ["beatmaps", "paged_embeds", "teams", "misc", "lobbies", "qualifier_results"]

for cog in cog_list:
    client.load_extension(cog)


@client.event
async def on_ready():
    db = read_tournament_db()
    guild = client.get_guild(402213530599948299)
    player_role = discord.utils.get(guild.roles, id=693574523324203009)

    print(f"Checking player roles..")
    for member in guild.members:
        if player_role in member.roles:
            id = str(member.id)
            if id not in get_players_by_discord():
                print(f"Removing {player_role} role from {member}")
                await member.remove_roles(player_role)

    for user in db["users"]:
        discord_id = user["discord_id"]
        discord_user = discord.utils.get(guild.members, id=discord_id)
        if player_role not in discord_user.roles:
            print(f"Adding {player_role} role to {discord_user}")
            await discord_user.add_roles(player_role)
    print(f"Bot Started!!")
    return


client.run(os.environ["TOKEN"])

