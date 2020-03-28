import os
import json
import requests
import math
from discord.ext import commands
from bs4 import BeautifulSoup

prefix = "?"

client = commands.Bot(command_prefix=prefix, case_insensitive=True)

rank_limit = 13200

@client.command(name='team')
async def create_team(ctx, osu_user2, team_name):
    """
    :param ctx:
    :param osu_user2: Komutu kullanan kişinin yanında turnuvaya katılacak olan 2. kişi
    :param team_name: Takım ismi
    :return: Verilen takım ismi ile takım oluşturur
    """

    if len(team_name) > 16:
        await ctx.send("Takım ismi 16 karakterden kısa olmalıdır.")
        return

    db = read_tournament_db()

    user1_discord_id = ctx.author.id
    user1_found = False
    for user in db["users"]:
        if user["discord_id"] == user1_discord_id:
            user1_found = True
            user1_rank = user["statistics"]["pp_rank"]

    if not user1_found:
        await ctx.send(f"Takım oluşturmadan önce turnuvaya kayıt olmalısın.\nKullanım: `{prefix}register`")
        return

    user2_discord_id = osu_user2[3:-1]
    try:
        user2_discord_id = int(user2_discord_id)
    except:
        await ctx.send(f"Kullanım: `{prefix}team @oyuncu takım_ismi`\n"
                       f"Ex: `{prefix}team @heyronii asdasfazamaz`")
        return

    user2_found = False
    for user in db["users"]:
        if user["discord_id"] == user2_discord_id:
            user2_rank = user["statistics"]["pp_rank"]
            user2_found = True
            break

    if not user2_found:
        await ctx.send(f"`{osu_user2}` kayıt olanlar arasında bulunamadı.")
        return

    for team in db["teams"]:
        user1_id = team["user1"]
        user2_id = team["user2"]
        team_name = team["name"]
        if user1_id == ctx.author.id or user2_id == ctx.author.id:
            await ctx.send(f"{ctx.author.mention} sen zaten `{team_name}` takımındasın!")
            return

        if user1_id == user2_discord_id or user2_id == user2_discord_id:
            await ctx.send(
                f"{osu_user2}, `{team_name}` takımında oyuncu! Takımından ayrılmadan onu takımına alamazsın.")
            return

    user1_weight = get_user_weight(user1_rank)
    user2_weight = get_user_weight(user2_rank)

    if user1_weight + user2_weight > rank_limit:
        await ctx.send(
            f"Takımın toplam değeri sınırın üzerinde kaldığı için katılamazsınız."
            f"\nTakımınızın toplam değeri: {user1_weight + user2_weight} > {rank_limit}")
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
    :param ctx:
    :return: Komutu kullanan kişiyi turnuvadan çıkarır
    """
    db = read_tournament_db()

    removed = False

    for user in db["users"]:
        if user["discord_id"] == ctx.author.id:
            uname = user["username"]
            removed = True
            await ctx.send(f"`{uname}` turnuvadan ayrıldı, tekrar görüşmek üzere.")
            db["users"].remove(user)
            break

    if not removed:
        await ctx.send(f"{ctx.author.mention} turnuvaya kayıtlı değilsin...")
        return

    for team in db["teams"]:
        u1_discord = team["user1"]["discord_id"]
        u2_discord = team["user2"]["discord_id"]

        if u1_discord == ctx.author.id or u2_discord == ctx.author.id:
            disband_team(team)
            team_name = team["name"]
            await ctx.send(
                f"`{team_name}` takımı bozuldu... <@{u2_discord if u1_discord == ctx.author.id else u1_discord}>")
            break

    updated_db = read_tournament_db()
    updated_db["users"] = db["users"]

    if not removed:
        await ctx.send(f"{ctx.author.mention} turnuvaya kayıtlı değilsin.")
    else:
        write_tournament_db(updated_db)

    return


@client.command(name='register')
async def register_tourney(ctx, osu_user1):
    """
    :param ctx:
    :param osu_user1: Turnuvaya katılacak kişinin osu! nicki veya id'si
    :return: Turnuvaya katılan kişileri listeye ekler
    """
    if not ctx.message.channel.guild.id == 402213530599948299:
        return

    db = read_tournament_db()

    for user in db["users"]:
        uname = user["username"]
        if user["discord_id"] == ctx.author.id:
            await ctx.send(
                f"Sen zaten turnuvaya `{uname}` adıyla kayıtlısın. Turnuvadan ayrılmak için: `{prefix}leave`")
            return
        if user["username"] == osu_user1 or str(user["id"]) == osu_user1:
            await ctx.send(f"Turnuvaya `{uname}` adıyla kayıt olunmuş. Turnuvadan ayrılmak için: `{prefix}leave`")
            return

    user1_info = get_user_info(osu_user1)

    user1_info["discord_id"] = ctx.author.id
    user1_weight = get_user_weight(user1_info["statistics"]["pp_rank"])
    user2_weight = rank_limit - user1_weight
    teammate_min_rank = float("inf")
    for rank in range(1, 100000):
        if get_user_weight(rank) < user2_weight:
            teammate_min_rank = rank
            break

    if teammate_min_rank == float("inf"):
        teammate_min_rank = 0

    db["users"].append(user1_info)

    write_tournament_db(db)

    await ctx.send(f"`{osu_user1}` başarıyla turnuvaya katıldın! Devam edebilmek için bir takım kurman gerekiyor:\n"
                   f"Kullanım: `{prefix}team @oyuncu takım_ismi`\n Ex. `{prefix}team @heyronii Yokediciler`\n"
                   f"Beraber katılabileceğin takım arkadaşın min {teammate_min_rank:0d} rank olabilir.")
    return


def get_user_info(username):
    r = requests.get(f"https://osu.ppy.sh/users/{username}")
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        json_user = soup.find(id="json-user").string
    except:
        raise Exception(f"`{username}` adlı kişiyi osu!'da bulamadım.")
    user_dict = json.loads(json_user)

    return user_dict


def read_tournament_db():
    tournament_db_file = "turnuva.json"

    if not os.path.exists(tournament_db_file):
        with open(tournament_db_file, "w", encoding='utf-8') as f:
            json.dump({"teams": [], "users": []}, f)

        return {"teams": [], "users": []}

    with open(tournament_db_file, "r", encoding='utf-8') as f:
        db = json.load(f)

    return db


def write_tournament_db(db):
    tournament_db_file = "turnuva.json"

    with open(tournament_db_file, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=2)

    return


def disband_team(team):
    db = read_tournament_db()
    if team in db["teams"]:
        db["teams"].remove(team)
    else:
        return -1
    write_tournament_db(db)
    return 0


client.run(os.environ["TOKEN"])
