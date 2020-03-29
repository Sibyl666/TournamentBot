import os
import json
import requests
import math
import discord
import asyncio
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
        guild = client.get_guild(402213530599948299)
        player_role = discord.utils.get(guild.roles, id=693574523324203009)
        discord_id = ctx.author.id
        discord_user = discord.utils.get(guild.members, id=discord_id)
        if player_role in discord_user.roles:
            await discord_user.remove_roles(player_role)

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
        guild = client.get_guild(402213530599948299)
        player_role = discord.utils.get(guild.roles, id=693574523324203009)
        discord_id = discord_id
        discord_user = discord.utils.get(guild.members, id=discord_id)
        if player_role in discord_user.roles:
            await discord_user.remove_roles(player_role)

        await ctx.send(f"`{osu_username}` turnuvadan ayrıldı, tekrar görüşmek üzere.")

    if ret["disbanded"]:
        team_name = info["team_name"]
        p2_discord = info["p2_discord"]
        await ctx.send(f"`{team_name}` takımı bozuldu... <@{p2_discord}>")

    return


async def create_paged_embed(ctx, data, fixed_fields, called_by):
    page_no = 1

    if called_by == "players":
        max_item_index = len(data["users"])
    if called_by == "teams":
        max_item_index = len(data["teams"])

    result_per_page = 16  # Show 16 results per page
    max_page = math.ceil(max_item_index / result_per_page)

    def get_desc_text(data, page_no, result_per_page, called_by):
        desc_text = ""
        if called_by == "players":
            show_data = data["users"][(page_no - 1) * result_per_page:page_no * result_per_page]
            for user_no, data_point in enumerate(show_data):
                has_team = False
                user_rank = data_point["statistics"]["pp_rank"]
                username = data_point["username"]
                user_discord_id = data_point["discord_id"]
                for team in data["teams"]:
                    team_name = team["name"]
                    p1_discord = team["user1"]
                    p2_discord = team["user2"]
                    if user_discord_id == p1_discord or user_discord_id == p2_discord:
                        has_team = True
                        desc_text += f"#{user_no + 1 + (page_no - 1) * result_per_page} - `{username}` - #{user_rank} - `{team_name}`\n"
                        break
                if not has_team:
                    desc_text += f"**#{user_no + 1 + (page_no - 1) * result_per_page} - `{username}` - #{user_rank}**\n"

        elif called_by == "teams":
            show_data = data["teams"][(page_no - 1) * result_per_page:page_no * result_per_page]
            for team_no, data_point in enumerate(show_data):
                team_name = data_point["name"]
                team_p1 = data_point["user1"]
                team_p2 = data_point["user2"]

                for user in data["users"]:
                    if team_p1 == user["discord_id"]:
                        team_p1_uname = user["username"]
                    if team_p2 == user["discord_id"]:
                        team_p2_uname = user["username"]

                desc_text += f"#{team_no + 1 + (page_no - 1) * result_per_page}: `{team_name}` - {team_p1_uname} & {team_p2_uname}\n"

        return desc_text

    desc_text = get_desc_text(data, page_no, result_per_page, called_by)

    embed = discord.Embed(description=desc_text, color=tournament_color)
    embed.set_author(name=fixed_fields["author_name"])
    embed.set_thumbnail(url=fixed_fields["thumbnail_url"])

    if max_page <= 1:
        await ctx.send(embed=embed)
        return
    else:
        embed.set_footer(text=f"Page {page_no} of {max_page}")
        msg = await ctx.send(embed=embed)
        reactmoji = ['⬅', '➡']
        while True:
            for react in reactmoji:
                await msg.add_reaction(react)

            def check_react(reaction, user):
                if reaction.message.id != msg.id:
                    return False
                if user != ctx.message.author:
                    return False
                if str(reaction.emoji) not in reactmoji:
                    return False
                return True

            try:
                res, user = await client.wait_for('reaction_add', timeout=30.0, check=check_react)
            except asyncio.TimeoutError:
                return await msg.clear_reactions()

            if user != ctx.message.author:
                pass
            elif '⬅' in str(res.emoji):
                page_no -= 1
                if page_no < 1:
                    page_no = max_page

                desc_text = get_desc_text(data, page_no, result_per_page, called_by)
                embed2 = discord.Embed(description=desc_text, color=tournament_color)
                embed2.set_author(name=fixed_fields["author_name"])
                embed2.set_thumbnail(url=fixed_fields["thumbnail_url"])
                embed2.set_footer(text=f"Page {page_no} of {max_page}")

                await msg.clear_reactions()
                await msg.edit(embed=embed2)

            elif '➡' in str(res.emoji):
                page_no += 1
                if page_no > max_page:
                    page_no = 1

                desc_text = get_desc_text(data, page_no, result_per_page, called_by)
                embed2 = discord.Embed(description=desc_text, color=tournament_color)
                embed2.set_author(name=fixed_fields["author_name"])
                embed2.set_thumbnail(url=fixed_fields["thumbnail_url"])
                embed2.set_footer(text=f"Page {page_no} of {max_page}")

                await msg.clear_reactions()
                await msg.edit(embed=embed2)


@client.command(name='players')
async def show_registered_players(ctx):
    """
    Turnuvaya kayıtlı oyuncuları gösterir.
    """
    data = read_tournament_db()

    fixed_fields = {"author_name": "112'nin Corona Turnuvası Oyuncu Listesi",
                    "thumbnail_url": "https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png"}

    await create_paged_embed(ctx, data, fixed_fields, "players")
    return


@client.command(name='teams')
async def show_registered_teams(ctx):
    """
    Turnuvaya kayıtlı takımları gösterir.
    """

    db = read_tournament_db()

    fixed_fields = {"author_name": "112'nin Corona Turnuvası Takım Listesi",
                    "thumbnail_url": "https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png"}

    await create_paged_embed(ctx, db, fixed_fields, "teams")

    return


@client.command(name='register')
async def register_tourney(ctx, osu_user1):
    """
    Turnuvaya katılan kişiyi listeye ekler.

    osu_user1: Turnuvaya katılacak kişinin osu! nicki veya id'si
    """
    # if not ctx.message.channel.guild.id == 402213530599948299:
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

    teammate_min_rank = binary_search(user2_weight)

    db["users"].append(user1_info)

    write_tournament_db(db)

    guild = client.get_guild(402213530599948299)
    player_role = discord.utils.get(guild.roles, id=693574523324203009)
    if player_role not in ctx.author.roles:
        await ctx.author.add_roles(player_role)

    await ctx.send(f"`{osu_user1}` başarıyla turnuvaya katıldın! Devam edebilmek için bir takım kurman gerekiyor:\n"
                   f"Kullanım: `{prefix}team @oyuncu takım_ismi`\n Ex. `{prefix}team @heyronii Yokediciler`\n"
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
    db = read_tournament_db()

    if rank is not None:
        try:
            p1_rank = int(rank)
        except:
            await ctx.send(f"Usage: {prefix}rankcheck <optional: rank>")

    user_found = False
    for user in db["users"]:
        if user["discord_id"] == ctx.author.id:
            user1_info = user
            user_found = True
            break

    if not user_found:
        await ctx.send(f"Turnuvaya kayıtlı değilsin...")
        return

    if rank is not None:
        user1_weight = get_user_weight(p1_rank)
    else:
        user1_weight = get_user_weight(user1_info["statistics"]["pp_rank"])
    user2_weight = rank_limit - user1_weight
    teammate_min_rank = binary_search(user2_weight)

    await ctx.send(f"Beraber katılabileceğin takım arkadaşın {teammate_min_rank:0d}+ rank olabilir.")
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

players_by_discord = {}

for player in read_tournament_db()["users"]:
    discord_id = str(player["discord_id"])
    players_by_discord[discord_id] = player

client.run(os.environ["TOKEN"])
