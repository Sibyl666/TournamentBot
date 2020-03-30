import os
import json
import requests
import math
import discord
import asyncio
from oppai import *
from copy import deepcopy
from discord.ext import commands
from bs4 import BeautifulSoup

prefix = "?"

client = commands.Bot(command_prefix=prefix, case_insensitive=True)

tournament_color = discord.Color.from_rgb(177, 29, 160)
old_maps_filename = "old_maps.tsv"
mappool_db_file = "beatmaps.json"
tournament_db_file = "turnuva.json"
mod_colors = [(217, 217, 217), (255, 229, 153), (234, 153, 153), (180, 167, 214), (182, 215, 168), (241, 194, 50)]
rank_limit = 13200

@client.command(name="ping")
async def mappool_show(ctx, player):
    db = read_tournament_db()

    for user in db["users"]:
        if player == user["username"]:
            discord_user = discord.utils.get(ctx.guild.members, id = user["discord_id"])
            await ctx.send(discord_user.mention)
            return
    
    

@client.command(name='poolshow')
async def mappool_show(ctx, which_pool, mod):
    mappool_db = read_mappool_db()

    mods = ["NM", "HD", "HR", "DT", "FM", "TB"]
    which_pool = which_pool.upper()
    mod = mod.upper()
    mod_index = mods.index(mod)
    r, g, b = mod_colors[mod_index]
    color = discord.Color.from_rgb(r, g, b)
    desc_text = ""
    bmaps = [(bmap_id, bmap) for bmap_id, bmap in mappool_db.items() if
             bmap["mappool"] == which_pool and bmap["modpool"] == mod]

    author_name = f"112'nin Corona Turnuvası Beatmaps in {which_pool} - {mod}"

    for bmap_id, bmapset in bmaps:
        bmap = next(item for item in bmapset["beatmaps"] if item["id"] == int(bmap_id))
        '''
        cs = bmap["cs"]
        ar = bmap["ar"]
        od = bmap["accuracy"]
        hp = bmap["drain"]
        '''
        bpm = bmap["bpm"]
        length = bmap["hit_length"]
        star_rating = bmap["difficulty_rating"]
        '''
        if mod == "HR":
            cs = min(10, cs * 1.3)
            ar = min(10, ar * 1.4)
            od = min(10, od * 1.4)
            hp = min(10, hp * 1.4)
        '''
        if mod == "DT":
            length = length // 1.5
            bpm = bpm * 1.5

        bmap_url = bmap['url']
        bmap_name = f"{bmapset['artist']} - {bmapset['title']} [{bmap['version']}]"
        # embed.add_field(name=f"{bmap_name}", value=f"{bmap_url}", inline=False)
        desc_text += f"▸[{bmap_name}]({bmap_url})\n" \
                     f"▸Length: {length // 60}:{length % 60:02d} ▸Bpm: {bpm} ▸SR: {star_rating}* \n\n"
    embed = discord.Embed(description=desc_text, color=color)
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
    embed.set_author(name=author_name)
    embed.set_image(url="")

    await ctx.send(embed=embed)

    return


@client.command(name='mappool')
@commands.has_role("Mappool")
async def mappool(ctx, action, map_link=None, which_pool=None, mod=None, comment=""):
    """
    Add, remove or show maps from the mappools

    action: "add", "remove" or "show"
    map_link: (Optional) Link of the map you want to add or remove
    which_pool: (Optional) Which week's pool do you want to add this map? (qf, w1, w2)
    mod: (Optional) Which mod pool is this map going to be added? (nm, hd, hr, dt, fm, tb)
    comment: (Optional) Comment about the beatmap ("slow finger control, bit of alt"). Should be in quotation marks. Can be empty
    """
    if action.lower() == "add":
        which_pool = which_pool.upper()
        mod = mod.upper()
        if map_link is None or mod is None or which_pool is None:
            await ctx.send("You should add map link, pool and mod to the query.\n"
                           "Ex. `?mappool add https://osu.ppy.sh/beatmapsets/170942#osu/611679 qf NM`")
            return

        pools = ["QF", "W1", "W2"]
        if which_pool not in pools:
            await ctx.send(f"Mappools can only be QF, W1 or W2.\n"
                           f"You wanted to add to {which_pool}. There's no pool option for that.")
            return

        if not (map_link.startswith("http://") or map_link.startswith("https://")):
            await ctx.send(f"Map link should start with http:// or https://.\n"
                           f"You linked <{map_link}>, I don't think it's a valid link.")
            return

        map_id = map_link.split("/")[-1]
        try:
            map_id_int = int(map_id)
        except:
            await ctx.send(f"Map link seems wrong. Please check again. \n"
                           f"You linked <{map_link}> but I couldn\'t find beatmap id from it.")
            return

        mods = ["NM", "HD", "HR", "DT", "FM", "TB"]

        if which_pool == "QF":
            mods = mods[:4]

        if mod not in mods:
            await ctx.send(f"Mods can only be one of from {mods}.\n"
                           f"You wanted to select {mod} mod pool, but it does not exist.")
            return

        old_maps_list = get_old_maps()
        if map_id in old_maps_list:
            await ctx.send(f"The map you linked has been used in the previous iterations of this tournament.\n"
                           f"You linked <{map_link}>")
            return

        map_info, ezpp_map = get_map_info(map_id)
        if mod == "HR":
            ezpp_set_mods(ezpp_map, MODS_HR)
        elif mod == "DT":
            ezpp_set_mods(ezpp_map, MODS_DT)
        print(ezpp_mods(ezpp_map))
        stars = ezpp_stars(ezpp_map)

        selected_bmap = None
        for bmap in map_info["beatmaps"]:
            if bmap["id"] == map_id_int:
                selected_bmap = bmap
                break

        if selected_bmap is None:
            await ctx.send(f"<@!146746632799649792> something went wrong.\n"
                           f"Requested command: {prefix}{ctx.command.name} {ctx.args[1:]}")
            return

        bmap_artist = map_info["artist"]
        bmap_title = map_info["title"]
        bmap_creator = map_info["creator"]
        bmap_cover = map_info["covers"]["cover"]
        bmap_url = selected_bmap["url"]
        bmap_version = selected_bmap["version"]

        selected_bmap["difficulty_rating"] = f"{stars:.2f}"
        map_info["mappool"] = which_pool
        map_info["modpool"] = mod
        map_info["added_by"] = ctx.author.name
        map_info["comment"] = comment

        map_name = f"{bmap_artist} - {bmap_title} [{bmap_version}]"

        mappool_db = read_mappool_db()

        if which_pool == "QF":
            max_maps = [3, 2, 2, 2]
        else:
            max_maps = [5, 3, 3, 3, 3, 1]

        mod_index = mods.index(mod)
        max_map_in_pool = max_maps[mod_index]

        maps_in_pool = 0
        for k, v in mappool_db.items():
            if v["mappool"] == which_pool and v["modpool"] == mod:
                maps_in_pool += 1

        mappool_db[map_id] = map_info
        if maps_in_pool > max_map_in_pool:
            author_name = f"Couldn't add map to {which_pool} Pool - {mod}"
            title_text = map_name
            desc_text = "Map couldn't be added to the pool, because pool is full!"
            bmap_cover = ""
            footer_text = f"{max_map_in_pool} out of {max_map_in_pool} maps in {which_pool} {mod} pool"
        else:
            title_text = map_name
            author_name = f"Successfully added map to {which_pool} Pool - {mod}"
            desc_text = ""
            footer_text = f"{maps_in_pool + 1} out of {max_map_in_pool} maps in {which_pool} {mod} pool"
            write_mappool_db(mappool_db)

        embed = discord.Embed(title=title_text, description=desc_text, color=tournament_color, url=bmap_url)
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
        embed.set_author(name=author_name)
        embed.set_image(url=bmap_cover)
        embed.set_footer(text=footer_text)

        await ctx.send(embed=embed)

    elif action.lower() == "remove":
        if map_link is None:
            await ctx.send("You should add map link to the query.\n"
                           "Ex. `?mappool remove https://osu.ppy.sh/beatmapsets/170942#osu/611679`")

        if not (map_link.startswith("http://") or map_link.startswith("https://")):
            await ctx.send(f"Map link should start with http:// or https://.\n"
                           f"You linked <{map_link}>, I don't think it's a valid link.")
            return

        map_id = map_link.split("/")[-1]
        try:
            map_id_int = int(map_id)
        except:
            await ctx.send(f"Map link seems wrong. Please check again. \n"
                           f"You linked <{map_link}> but I couldn\'t find beatmap id from it.")
            return

        mappool_db = read_mappool_db()

        try:
            del mappool_db[map_id]
        except KeyError as e:
            await ctx.send(f"The specified beatmap does not exist in the pools.\n"
                           f"You wanted to remove <{map_link}>.")
            return

        write_mappool_db(mappool_db)
        await ctx.send(f"Successfully deleted <{map_link}> from pools.")

        return


def get_old_maps():
    with open(old_maps_filename, "r") as f:
        old_maps = f.read().splitlines()

    old_map_ids = [bmap.split("\t")[7] for bmap in old_maps]

    return old_map_ids


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
        await ctx.send(f"Takım oluşturmadan önce turnuvaya kayıt olmalısın.\nKullanım: `{prefix}register`")
        return

    print(f"?team {osu_user2} {team_name}")
    if osu_user2.startswith("<@!"):
        user2_discord_id = osu_user2[3:-1]
    elif osu_user2.startswith("<@"):
        user2_discord_id = osu_user2[2:-1]
    else:
        await ctx.send(f"Kullanım: `{prefix}team @oyuncu takım_ismi`\n"
                       f"Ex: `{prefix}team @heyronii asdasfazamaz`")
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
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")

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
                embed2.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
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
                embed2.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
                embed2.set_footer(text=f"Page {page_no} of {max_page}")

                await msg.clear_reactions()
                await msg.edit(embed=embed2)


@client.command(name='players')
async def show_registered_players(ctx):
    """
    Turnuvaya kayıtlı oyuncuları gösterir.
    """
    data = read_tournament_db()

    fixed_fields = {"author_name": "112'nin Corona Turnuvası Oyuncu Listesi"}

    await create_paged_embed(ctx, data, fixed_fields, "players")
    return


@client.command(name='teams')
async def show_registered_teams(ctx):
    """
    Turnuvaya kayıtlı takımları gösterir.
    """

    db = read_tournament_db()

    fixed_fields = {"author_name": "112'nin Corona Turnuvası Takım Listesi"}

    await create_paged_embed(ctx, db, fixed_fields, "teams")

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
    """
    Katılabileceğiniz takım arkadaşınızın maximum rankını gösterir
    rank: Optional - Rank aralığını öğrenmek istediğiniz kişinin rankı
    """
    db = read_tournament_db()

    if rank is not None:
        try:
            p1_rank = int(rank)
            teammate_min_rank = get_teammate_rank(p1_rank)
        except:
            await ctx.send(f"Usage: {prefix}rankcheck <optional: rank>")
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


@client.command(name='teammate')
async def get_potential_teammates(ctx):
    """
    Senin rankına uygun olabilecek takım arkadaşlarını gösterir.
    """

    user = check_registration(ctx.author.id)
    if user is not None:
        user_rank = user["statistics"]["pp_rank"]
    else:
        await ctx.send(
            f"Turnuvaya kayıtlı değilsin, kayıt olmak için `{prefix}register <osu username>` komutunu kullan.\n"
            f"Yardım için `{prefix}help` yazabilirsin.")
        return

    teammate_min_rank = get_teammate_rank(user_rank)

    db = read_tournament_db()
    potential_teammates = deepcopy(db)

    for user in db["users"]:
        in_team = False
        for team in db["teams"]:
            p1_id = team["user1"]
            p2_id = team["user2"]
            if p1_id == user["discord_id"] or p2_id == user["discord_id"]:
                in_team = True

        if in_team or teammate_min_rank > user["statistics"]["pp_rank"]:
            potential_teammates["users"].remove(user)

    fixed_fields = {"author_name": "Sana uygun takım arkadaşları listesi"}

    await create_paged_embed(ctx, potential_teammates, fixed_fields, 'players')
    return


def get_teammate_rank(rank):
    user1_weight = get_user_weight(rank)
    user2_weight = rank_limit - user1_weight
    return binary_search(user2_weight)


def get_user_info(username):
    r = requests.get(f"https://osu.ppy.sh/users/{username}")
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        json_user = soup.find(id="json-user").string
    except:
        raise Exception(f"`{username}` adlı kişiyi osu!'da bulamadım.")
    user_dict = json.loads(json_user)

    return user_dict


def get_map_info(map_id):
    r = requests.get(f"https://osu.ppy.sh/b/{map_id}")
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        json_bmap = soup.find(id="json-beatmapset").string
    except:
        raise Exception(f"`{map_id}` id'li mapi osu!'da bulamadım.")
    bmap_dict = json.loads(json_bmap)

    try:
        osu_file = requests.get(f"https://bloodcat.com/osu/b/{map_id}")
    except:
        raise Exception(f"`{map_id}` bloodcat'te bulunamadı.")

    osu_file_contents = osu_file.content

    ezpp_map = ezpp_new()
    ezpp_set_autocalc(ezpp_map, 1)
    ezpp_data_dup(ezpp_map, osu_file_contents.decode('utf-8'), len(osu_file_contents))

    return bmap_dict, ezpp_map


def read_mappool_db():
    global mappool_db_file

    if not os.path.exists(mappool_db_file):
        with open(mappool_db_file, "w", encoding='utf-8') as f:
            json.dump({}, f)
        return {}

    with open(mappool_db_file, "r", encoding='utf-8') as f:
        db = json.load(f)

    return db


def write_mappool_db(db):
    global mappool_db_file

    with open(mappool_db_file, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=2)

    return


def read_tournament_db():
    global tournament_db_file

    if not os.path.exists(tournament_db_file):
        with open(tournament_db_file, "w", encoding='utf-8') as f:
            json.dump({"teams": [], "users": []}, f)

        return {"teams": [], "users": []}

    with open(tournament_db_file, "r", encoding='utf-8') as f:
        db = json.load(f)

    db["users"].sort(key=lambda e: e['statistics']['pp_rank'])

    return db


def write_tournament_db(db):
    global players_by_discord, tournament_db_file

    with open(tournament_db_file, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=2)

    players_by_discord = {}
    db["users"].sort(key=lambda e: e['statistics']['pp_rank'])

    for player in db["users"]:
        discord_id = str(player["discord_id"])
        players_by_discord[discord_id] = player

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


db = read_tournament_db()
players_by_discord = {}

for player in db["users"]:
    discord_id = str(player["discord_id"])
    players_by_discord[discord_id] = player

client.run(os.environ["TOKEN"])
