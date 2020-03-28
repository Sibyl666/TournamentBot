import os
import json
import requests
import math
import discord
from discord.ext import commands
from bs4 import BeautifulSoup

prefix = "?"

client = commands.Bot(command_prefix=prefix, case_insensitive=True)

tournament_color = discord.Color.from_rgb(177, 29, 160)
rank_limit = 13200


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

    if user2_discord_id == user1_discord_id:
        await ctx.send(f"Kendinle takım oluşturamazsın.")
        return

    user2_found = False
    for user in db["users"]:
        if user["discord_id"] == user2_discord_id:
            user2_rank = user["statistics"]["pp_rank"]
            user2_found = True
            break

    if not user2_found:
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

    if user1_weight + user2_weight > rank_limit:
        await ctx.send(
            f"Takımın toplam değeri sınırın üzerinde kaldığı için katılamazsınız."
            f"\nTakımınızın toplam değeri: {user1_weight + user2_weight:.0f} > {rank_limit}")
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
        await ctx.send(f"`{osu_username}` turnuvadan ayrıldı, tekrar görüşmek üzere.")

    if ret["disbanded"]:
        team_name = info["team_name"]
        p2_discord = info["p2_discord"]
        await ctx.send(f"`{team_name}` takımı bozuldu... <@{p2_discord}>")

    return


def remove_user_from_tournament(discord_id):
    db = read_tournament_db()

    true_falses = {"removed": False, "disbanded": False}
    info = {"osu_username": None, "p2_discord": None, "team_name": None}
    for user in db["users"]:
        if user["discord_id"] == discord_id:
            info["osu_username"] = user["username"]
            true_falses["removed"] = True
            db["users"].remove(user)
            break

    if not true_falses["removed"]:
        return None, None

    for team in db["teams"]:
        u1_discord = team["user1"]["discord_id"]
        u2_discord = team["user2"]["discord_id"]

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
async def kick_player(ctx, discord_id):
    """
    Oyuncuyu turnuvadan atar.

    osu_user2: Atmak istediğiniz oyuncunun nicki
    """
    try:
        discord_id = int(discord_id)
    except:
        await ctx.send("Geçerli discord id'si girin")

    ret, info = remove_user_from_tournament(discord_id)

    if ret is None:
        await ctx.send("Oyuncu bulunamadığı için kickleyemedik...")

    if ret["removed"]:
        osu_username = info["osu_username"]
        await ctx.send(f"`{osu_username}` turnuvadan ayrıldı, tekrar görüşmek üzere.")

    if ret["disbanded"]:
        team_name = info["team_name"]
        p2_discord = info["p2_discord"]
        await ctx.send(f"`{team_name}` takımı bozuldu... <@{p2_discord}>")

    return


async def create_paged_embed(ctx, data, fixed_fields):

    page_no = 1

    max_item_index = len(data)
    result_per_page = 5  # Show 5 results per page
    max_page = math.ceil(max_item_index / result_per_page)

    embed = discord.Embed()
    embed.set_author(name=fixed_fields["author_name"])
    embed.set_thumbnail(url=fixed_fields["thumbnail_url"])
    if max_page <= 1:
        await ctx.send()


@client.command(name='players')
async def show_registered_players(ctx):

    users = read_tournament_db()["users"]

    fixed_fields = {"author_name": "112'nin Corona Turnuvası Takım Listesi",
                    "thumbnail_url": "https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png"}

    desc_text = ""
    for user_no, user in enumerate(users):
        user_rank = user["statistics"]["pp_rank"]
        username = user["username"]
        desc_text += f"#{user_no} - {username} - #{user_rank}\n"

    embed = discord.Embed(description=f"{desc_text}", color=tournament_color)
    embed.set_author(name="112'nin Corona Turnuvası Takım Listesi")
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
    await ctx.send(embed=embed)


@client.command(name='teams')
async def show_registered_teams(ctx):
    """
    Turnuvaya kayıtlı takımları gösterir
    """

    db = read_tournament_db()

    fixed_fields = {"author_name": "112'nin Corona Turnuvası Takım Listesi",
                    "thumbnail_url": "https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png"}

    desc_text = ""
    for team_no, team in enumerate(db["teams"]):
        team_name = team["name"]
        team_p1 = team["user1"]
        team_p2 = team["user2"]

        for user in db["users"]:
            if team_p1 == user["discord_id"]:
                team_p1_uname = user["username"]
            if team_p2 == user["discord_id"]:
                team_p2_uname = user["username"]

        desc_text += f"#{team_no+1}: {team_name} - {team_p1_uname} & {team_p2_uname}\n"

    embed = discord.Embed(description=f"{desc_text}",
                          color=tournament_color)
    embed.set_author(name="112'nin Corona Turnuvası Takım Listesi")
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
    await ctx.send(embed=embed)

    #await create_paged_embed(ctx, teams, fixed_fields)

    return


@client.command(name='register')
async def register_tourney(ctx, osu_user1):
    """
    Turnuvaya katılan kişiyi listeye ekler

    osu_user1: Turnuvaya katılacak kişinin osu! nicki veya id'si
    """
    #if not ctx.message.channel.guild.id == 402213530599948299:
     #   return

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

    teammate_min_rank = binary_search(user2_weight)

    db["users"].append(user1_info)

    write_tournament_db(db)

    await ctx.send(f"`{osu_user1}` başarıyla turnuvaya katıldın! Devam edebilmek için bir takım kurman gerekiyor:\n"
                   f"Kullanım: `{prefix}team @oyuncu takım_ismi`\n Ex. `{prefix}team @heyronii Yokediciler`\n"
                   f"Beraber katılabileceğin takım arkadaşın {teammate_min_rank:0d}+ rank olabilir.")
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


@client.event
async def on_ready():
    print(f"Bot Started!!")
    read_tournament_db()
    return


client.run(os.environ["TOKEN"])
