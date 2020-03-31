import os
import json
import requests
import math
import discord
import asyncio
from copy import deepcopy
from discord.ext import commands
from bs4 import BeautifulSoup

from database import read_tournament_db, write_tournament_db , get_settings
from requester import get_user_info

settings = get_settings()

client = commands.Bot(command_prefix=settings['prefix'], case_insensitive=True)
client.load_extension("beatmaps")
client.load_extension("page_embed_new")


@client.command(name="ping")
async def ping(ctx, player):
    db = read_tournament_db()

    for user in db["users"]:
        if player.lower() == user["username"].lower():
            discord_user = discord.utils.get(ctx.guild.members, id = user["discord_id"])
            await ctx.send(discord_user.mention)
            return




@client.command(name='team')
async def create_team(ctx, osu_user2, team_name):
    """
    Verilen takım ismi ve oyuncu ile takım oluşturur.

    osu_user2: Komutu kullanan kişinin yanında turnuvaya katılacak olan 2. kişi
    team_name: Takımın ismi

    Komutu kullanan kişi otomatik olarak takım lideri seçilecektir.
    """

    if len(team_name) > 16:
        await ctx.send("Takım ismi 16 karakterden kısa olmalıdır.")
        return

    db = read_tournament_db()

    user1 = check_registration(ctx.author.id)
    if user1 is not None:
        user1_rank = user1["statistics"]["pp_rank"]
    else:
        await ctx.send(f"Takım oluşturmadan önce turnuvaya kayıt olmalısın.\nKullanım: `{settings['prefix']}register`")
        return

    print(f"?team {osu_user2} {team_name}")
    if osu_user2.startswith("<@!"):
        user2_discord_id = osu_user2[3:-1]
    elif osu_user2.startswith("<@"):
        user2_discord_id = osu_user2[2:-1]
    else:
        await ctx.send(f"Kullanım: `{settings['prefix']}team @oyuncu takım_ismi`\n"
                       f"Ex: `{settings['prefix']}team @heyronii asdasfazamaz`")
        return
    user2_discord_id = int(user2_discord_id)

    if user2_discord_id == ctx.author.id:
        await ctx.send(f"Kendinle takım oluşturamazsın.")
        return

    user2 = check_registration(user2_discord_id)

    if user2 is not None:
        user2_rank = user2["statistics"]["pp_rank"]
    else:
        await ctx.send(f"{osu_user2} kayıt olanlar arasında bulunamadı.")
        return

    for team in db["teams"]:
        user1_id = team["user1"]
        user2_id = team["user2"]
        team_name_from_db = team["name"]
        if user1_id == ctx.author.id or user2_id == ctx.author.id:
            await ctx.send(f"{ctx.author.mention} sen zaten `{team_name_from_db}` takımındasın!")
            return

        if user1_id == user2_discord_id or user2_id == user2_discord_id:
            await ctx.send(
                f"{osu_user2}, `{team_name_from_db}` takımında oyuncu! Takımından ayrılmadan onu takımına alamazsın.")
            return

    user1_weight = get_user_weight(user1_rank)
    user2_weight = get_user_weight(user2_rank)

    if user1_weight + user2_weight > settings["rank_limit"] :
        await ctx.send(
            f"Takımın toplam değeri sınırın üzerinde kaldığı için katılamazsınız."
            f"\nTakımınızın toplam değeri: {user1_weight + user2_weight:.0f} > {settings['rank_limit']}")
    else:
        new_team = {"name": team_name, "user1": ctx.author.id, "user2": user2_discord_id}
        db["teams"].append(new_team)
        await ctx.send(f"`{team_name}` başarıyla turnuvaya katıldı!")

    write_tournament_db(db)
    return


def get_user_weight(rank):
    # Ugly function to calculate user's rank weight
    return (19273 - 1371 * math.log(rank + 1000)) - (1000 * (1371 / (rank + 1000)))


@client.command(name='leave')
async def remove_user(ctx):
    """
    Komutu kullanan kişiyi turnuvadan çıkarır.
    İçinde bulunduğu takım varsa, bozulur.
    """
    ret, info = remove_user_from_tournament(ctx.author.id)

    if ret is None:
        await ctx.send(f"{ctx.author.mention} turnuvaya kayıtlı değilsin...")

    if ret["removed"]:
        osu_username = info["osu_username"]
        await remove_user_role(ctx.author.id)
        await ctx.send(f"`{osu_username}` turnuvadan ayrıldı, tekrar görüşmek üzere.")

    if ret["disbanded"]:
        team_name = info["team_name"]
        p2_discord = info["p2_discord"]
        await ctx.send(f"`{team_name}` takımı bozuldu... <@{p2_discord}>")

    return


async def remove_user_role(discord_id):
    guild = client.get_guild(402213530599948299)
    player_role = discord.utils.get(guild.roles, id=693574523324203009)
    discord_user = discord.utils.get(guild.members, id=discord_id)
    if player_role in discord_user.roles:
        await discord_user.remove_roles(player_role)

    return


def remove_user_from_tournament(discord_id):
    db = read_tournament_db()

    true_falses = {"removed": False, "disbanded": False}
    info = {"osu_username": None, "p2_discord": None, "team_name": None}
    user = check_registration(discord_id)
    if user is not None:
        info["osu_username"] = user["username"]
        true_falses["removed"] = True
        db["users"].remove(user)
    else:
        return None, None

    for team in db["teams"]:
        u1_discord = team["user1"]
        u2_discord = team["user2"]

        if u1_discord == discord_id or u2_discord == discord_id:
            disband_team(team)
            info["team_name"] = team["name"]
            info["p2_discord"] = u2_discord if u1_discord == discord_id else u1_discord
            true_falses["disbanded"] = True
            break

    updated_db = read_tournament_db()
    updated_db["users"] = db["users"]
    write_tournament_db(updated_db)

    return true_falses, info


@client.command(name='kick')
@commands.has_permissions(administrator=True)
async def kick_player(ctx, osu_username):
    """
    Oyuncuyu turnuvadan atar.

    osu_username: Atmak istediğiniz oyuncunun osu! nicki
    """
    discord_id = "sdfgadfg"
    db = read_tournament_db()
    for user in db["users"]:
        if user["username"] == osu_username:
            discord_id = user["discord_id"]

    try:
        discord_id = int(discord_id)
    except:
        await ctx.send("Geçerli bir oyuncu ismi girin")

    ret, info = remove_user_from_tournament(discord_id)

    if ret is None:
        await ctx.send("Oyuncu bulunamadığı için kickleyemedik...")

    if ret["removed"]:
        osu_username = info["osu_username"]
        await remove_user_role(discord_id)
        await ctx.send(f"`{osu_username}` turnuvadan ayrıldı, tekrar görüşmek üzere.")

    if ret["disbanded"]:
        team_name = info["team_name"]
        p2_discord = info["p2_discord"]
        await ctx.send(f"`{team_name}` takımı bozuldu... <@{p2_discord}>")

    return



@client.command(name='register')
async def register_tourney(ctx, osu_user1):
    """
    Turnuvaya katılan kişiyi listeye ekler.

    osu_user1: Turnuvaya katılacak kişinin osu! nicki veya id'si
    """
    # if not ctx.message.channel.guild.id == 402213530599948299:
    #    return

    db = read_tournament_db()

    for user in db["users"]:
        uname = user["username"]
        if user["discord_id"] == ctx.author.id:
            await ctx.send(
                f"Sen zaten turnuvaya `{uname}` adıyla kayıtlısın. Turnuvadan ayrılmak için: `{settings['prefix']}leave`")
            return
        if user["username"] == osu_user1 or str(user["id"]) == osu_user1:
            await ctx.send(f"Turnuvaya `{uname}` adıyla kayıt olunmuş. Turnuvadan ayrılmak için: `{settings['prefix']}leave`")
            return

    user1_info = get_user_info(osu_user1)

    user1_info["discord_id"] = ctx.author.id
    teammate_min_rank =get_teammate_rank(user1_info["statistics"]["pp_rank"])

    db["users"].append(user1_info)

    write_tournament_db(db)

    guild = client.get_guild(402213530599948299)
    player_role = discord.utils.get(guild.roles, id=693574523324203009)
    if player_role not in ctx.author.roles:
        await ctx.author.add_roles(player_role)

    await ctx.send(f"`{osu_user1}` başarıyla turnuvaya katıldın! Devam edebilmek için bir takım kurman gerekiyor:\n"
                   f"Kullanım: `{settings['prefix']}team @oyuncu takım_ismi`\n Ex. `{settings['prefix']}team @heyronii Yokediciler`\n"
                   f"Beraber katılabileceğin takım arkadaşın {teammate_min_rank:0d}+ rank olabilir.")
    return


def binary_search(weight):
    rank_upper = 100000000
    rank_lower = 1
    while not rank_upper == rank_lower:
        rank_mid = (rank_upper + rank_lower) // 2
        temp_weight = get_user_weight(rank_mid)
        if weight > temp_weight:
            rank_upper = rank_mid
        else:
            rank_lower = rank_mid + 1

    return rank_mid


@client.command(name='rankcheck')
async def check_player_rank(ctx, rank=None):
    """
    Katılabileceğiniz takım arkadaşınızın maximum rankını gösterir
    rank: Optional - Rank aralığını öğrenmek istediğiniz kişinin rankı
    """

    if rank is not None:
        try:
            p1_rank = int(rank)
            teammate_min_rank = get_teammate_rank(p1_rank)
        except:
            await ctx.send(f"Usage: {settings['prefix']}rankcheck <optional: rank>")
            return
    else:
        user = check_registration(ctx.author.id)
        if user is not None:
            user1_info = user
        else:
            await ctx.send(f"Turnuvaya kayıtlı değilsin...")
            return

        teammate_min_rank = get_teammate_rank(user1_info["statistics"]["pp_rank"])

    await ctx.send(f"Beraber katılabileceğin takım arkadaşın {teammate_min_rank:0d}+ rank olabilir.")
    return


def check_registration(user_discord):
    user_discord = str(user_discord)

    if user_discord in players_by_discord:
        user = players_by_discord[user_discord]
        return user
    else:
        return None



def get_teammate_rank(rank):
    user1_weight = get_user_weight(rank)
    user2_weight = settings["rank_limit"] - user1_weight
    return binary_search(user2_weight)



def disband_team(team):
    db = read_tournament_db()
    if team in db["teams"]:
        db["teams"].remove(team)
    else:
        return -1
    write_tournament_db(db)
    return 0


@client.event
async def on_ready():
    print(f"Bot Started!!")
    db = read_tournament_db()
    guild = client.get_guild(402213530599948299)
    player_role = discord.utils.get(guild.roles, id=693574523324203009)

    for member in guild.members:
        if player_role in member.roles:
            id = str(member.id)
            if id not in players_by_discord:
                print(f"Removing {player_role} role from {member}")
                await member.remove_roles(player_role)

    for user in db["users"]:
        discord_id = user["discord_id"]
        discord_user = discord.utils.get(guild.members, id=discord_id)
        if player_role not in discord_user.roles:
            print(f"Adding {player_role} role to {discord_user}")
            await discord_user.add_roles(player_role)
    return


db = read_tournament_db()
players_by_discord = {}

for player in db["users"]:
    discord_id = str(player["discord_id"])
    players_by_discord[discord_id] = player

client.run(os.environ["Token"])