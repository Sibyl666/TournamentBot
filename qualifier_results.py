import discord
import math
import time
from copy import deepcopy
from discord.ext import commands

from database import read_qualifier_results_db, write_qualifier_results_db, get_old_maps, get_settings ,read_tournament_db, read_lobby_db, write_lobby_db
from requester import get_match_info

settings = get_settings()
qualifier_channel_id = 697002041603653663
lobby_channel_id = 695995975189135430
max_team_per_page = 8


def get_players_with_teams():
    data = read_tournament_db()
    team_list = []
    for data_point in data["teams"]:
        team_p1 = data_point["user1"]
        team_p2 = data_point["user2"]
        team = {"team_name": data_point["name"]}
        for user in data["users"]:
            if team_p1 == user["discord_id"]:
                team["player_1_id"] = user["id"]
                team["player_1_name"] = user["username"]
                team["player_1_score"] = 0
            if team_p2 == user["discord_id"]:
                team["player_2_id"] = user["id"]
                team["player_2_name"] = user["username"]
                team["player_1_score"] = 0
        team_list.append(team)

    return team_list

def get_players_for_total_results():
    data = read_tournament_db()
    team_list = []
    for data_point in data["teams"]:
        team = {"team_name": data_point["name"], "total_score": 0}
        team_list.append(team)
    return team_list


def get_message_ids():
    
    qualifier_results_db = read_qualifier_results_db()
    maps_db = qualifier_results_db["maps"]
    
    message_list = []
    result_id = qualifier_results_db["final_result"]["message_id"]
    if result_id is not None:
        message_list.append(result_id)
    for map_id, data in maps_db.items():
        if data["qualifier_message_id"] is not None:
            message_list.append(data["qualifier_message_id"])
    return message_list

def calculate_final_results(qualifier_results_db):
    maps_db = qualifier_results_db["maps"]

    team_list = get_players_for_total_results()
    for map_id, map_data in maps_db.items():
        
        scores = map_data["qualifier_scores"]

        for index, score in enumerate(scores):
            for team in team_list:
                if team["team_name"] == score["team_name"]:
                    team["total_score"] += index + 1
                    break

    return_array = []
    for team in team_list:
        if team["total_score"] != 0:
            team["total_score"] = team["total_score"] / len(maps_db)
            return_array.append(team)

    return_array.sort(key=lambda x: x["total_score"])
    return return_array
        

class Results(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.message_list = get_message_ids()
        self.last_executions = {}

    async def create_embed_for_qualifier(self, maps_db, map_id, page=1):
        
        scores = maps_db[map_id]["qualifier_scores"]
        
        desc_text = ""
        for index, team in enumerate(scores[(page-1)*max_team_per_page : page*max_team_per_page]):

            total_score = team["player_1_score"] + team["player_2_score"]
            desc_text += f"**#{index+1+((page-1)*max_team_per_page)}** - `{team['team_name']}`  ▸Toplam Skor: {'{:,}'.format(total_score)}\n" \
                         f" ▸{team['player_1_name']}: {'{:,}'.format(team['player_1_score'])}  ▸{team['player_2_name']}: {'{:,}'.format(team['player_2_score'])}\n \n"

        mod = maps_db[map_id]["modpool"]
        color = discord.Color.from_rgb(*settings["mod_colors"][mod])
        url = f"https://osu.ppy.sh/b/{map_id}"

        artist = maps_db[map_id]["artist"]
        title = maps_db[map_id]["title"]
        diff_name = maps_db[map_id]["diff_name"]
            
        embed = discord.Embed(description=desc_text, title=f"{artist} {title}[{diff_name}]",
                                  color=color)
        embed.set_author(name=f"112'nin Corona Turnuvası - Sıralama Sonuçları")
        embed.set_thumbnail(url=settings["mod_icons"][mod])
        embed.url = url
        embed.set_footer(text=f"Page {page} of {math.ceil(len(scores)/max_team_per_page)}")

        return embed

    async def create_embed_for_final_results(self, total_scores, page=1):
        desc_text = ""
        
        seeds = ["Top Seed", "High Seed", "Mid Seed", "Low Seed", "Elenenler"]
        if page>2:
            desc_text +=f"__**{seeds[4]}**__ \n"
        for index, team in enumerate(total_scores[(page-1)*max_team_per_page : page*max_team_per_page]):
            if index %4 == 0 and page <= 2:
                desc_text +=f"__**{seeds[ ((page-1)*2)+index//4 ]}**__ \n"
            
            desc_text += f"**▸#{index+1+((page-1)*max_team_per_page)}** - `{team['team_name']}` - {'{:.2f}'.format(team['total_score'])}\n"
        
        
        embed = discord.Embed(description=desc_text, color=discord.Color.from_rgb(*settings["tournament_color"]))
        embed.set_author(name=f"112'nin Corona Turnuvası - Sıralama Sonuçları")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
        embed.set_footer(text=f"Page {page} of {math.ceil(len(total_scores)/max_team_per_page)}")
        
        return embed

    @commands.command(name="showfinalresult")
    @commands.has_permissions(administrator=True)
    async def show_final_results(self, ctx):
        qualifier_results_db = read_qualifier_results_db()
        final_resuts = qualifier_results_db["final_result"]
        
        embed = await self.create_embed_for_final_results(final_resuts["final_scores"])
        msg = await ctx.send(embed=embed)
        if len(final_resuts["final_scores"]) > max_team_per_page:
            await msg.add_reaction("⬅")
            await msg.add_reaction("➡")

        final_resuts["message_id"] = msg.id
        self.message_list.append(msg.id)
        write_qualifier_results_db(qualifier_results_db)


    @commands.command(name="showresult")
    @commands.has_permissions(administrator=True)
    async def show_qualifier_map_results(self, ctx, map_id):
        qualifier_results_db = read_qualifier_results_db()
        maps_db = qualifier_results_db["maps"]
        
        try:
            embed = await self.create_embed_for_qualifier(maps_db, map_id)
        except KeyError:
            ctx.send("Aranan map bulunamadı")

        msg = await ctx.send(embed=embed)
        if len(maps_db[map_id]["qualifier_scores"]) > max_team_per_page:
            await msg.add_reaction("⬅")
            await msg.add_reaction("➡")

        maps_db[map_id]["qualifier_message_id"] = msg.id
        self.message_list.append(msg.id)
        write_qualifier_results_db(qualifier_results_db)
    
    @commands.command(name="removeresult")
    @commands.has_permissions(administrator=True)
    async def delete_results(self, ctx, map_id):
        qualifier_results_db = read_qualifier_results_db()
        channel = discord.utils.get(ctx.message.guild.channels, id=qualifier_channel_id)
        if map_id == "final":
            final_results_db = qualifier_results_db["final_result"]
            
            msg = await channel.fetch_message(final_results_db["message_id"])
            await msg.delete()
            final_results_db["message_id"] = None

        else:
            maps_db = qualifier_results_db["maps"]
            
            if maps_db[map_id]["qualifier_message_id"] is not None:
                msg = await channel.fetch_message(maps_db[map_id]["qualifier_message_id"])
                await msg.delete()
                maps_db[map_id]["qualifier_message_id"] = None
            else:
                await ctx.send (f"`{map_id}` mapı için sonuç mesajı yok.")
                return

        write_qualifier_results_db(qualifier_results_db)
        await ctx.send(f"{map_id} sonuçları başarıyla silindi.")
    
    @commands.command(name='addmplink')
    @commands.has_role("Hakem")
    async def add_mp_link_to_lobby(self, ctx, lobby_name, mp_link):
        """
        Odaya bir Mp Linki ekleyin
        lobby_name: Eklemek istediğiniz odanın adı
        mp_link: Maç linki
        """
        lobbies = read_lobby_db()
        
        if lobby_name not in lobbies:
            await ctx.send(f"`{lobby_name}` adında bir lobi yok..")
            return
        
        if lobbies[lobby_name]["referee_discord_id"] != ctx.author.id:
            await ctx.send(f"`{lobby_name}` adındaki lobide hakem değilsin.")
            return
        else:
            msg_id = lobbies[lobby_name]["msg_id"]
            channel = discord.utils.get(ctx.message.guild.channels, id=lobby_channel_id)#add it to settings
            msg = await channel.fetch_message(msg_id)
            
            embed = msg.embeds[0].copy()
            embed.url = mp_link
            await msg.edit(embed=embed)
            
            lobbies[lobby_name]["mp_link"] = mp_link
            write_lobby_db(lobbies)
            

        match_data = get_match_info(mp_link)
        qualifier_results_db = read_qualifier_results_db()
        maps_db = qualifier_results_db["maps"]
        teams = get_players_with_teams()

        channel = discord.utils.get(ctx.message.guild.channels, id=qualifier_channel_id)

        for game in match_data:
            current_teams = deepcopy(teams)
            for team in current_teams:
                write = False
                for scores in game["scores"]:
                    score = int(scores["score"])
                    if score != 0:
                        if scores["user_id"] == str(team["player_1_id"]):
                            team["player_1_score"] = int(scores["score"])
                            write = True
                        if scores["user_id"] == str(team["player_2_id"]):
                            team["player_2_score"] = int(scores["score"])
                            write = True
                        
                if write:
                    for index, data in enumerate(maps_db[game["beatmap_id"]]["qualifier_scores"]):
                        if team["team_name"] == data["team_name"] and data["player_1_score"] :
                            del maps_db[game["beatmap_id"]]["qualifier_scores"][index]
                            break
                            
                    maps_db[game["beatmap_id"]]["qualifier_scores"].append(team)
            
            maps_db[game["beatmap_id"]]["qualifier_scores"].sort(key=lambda x: x["player_1_score"]+x["player_2_score"], reverse=True)

            if maps_db[game["beatmap_id"]]["qualifier_message_id"] is not None:

                msg = await channel.fetch_message(maps_db[game["beatmap_id"]]["qualifier_message_id"])

                embed = await self.create_embed_for_qualifier(maps_db, game["beatmap_id"])
                await msg.edit(embed=embed)
                if len(maps_db[game["beatmap_id"]]["qualifier_scores"]) > max_team_per_page:
                    await msg.add_reaction("⬅")
                    await msg.add_reaction("➡")

        final_results_db = qualifier_results_db["final_result"]
        final_results_db["final_scores"] = calculate_final_results(qualifier_results_db)

        if final_results_db["message_id"] is not None:
            msg = await channel.fetch_message(final_results_db["message_id"])
            embed = await self.create_embed_for_final_results(final_results_db["final_scores"])
            await msg.edit(embed=embed)
            if len(final_results_db["final_scores"]) > max_team_per_page:
                    await msg.add_reaction("⬅")
                    await msg.add_reaction("➡")

        write_qualifier_results_db(qualifier_results_db)
        await ctx.send(f"`{ctx.author.name}`, `{lobby_name}` lobisine mp link eklendi.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        
        if payload.message_id in self.message_list:
            if payload.member != self.bot.user:
                channel = discord.utils.get(self.bot.get_all_channels(), id=qualifier_channel_id)
                msg = await channel.fetch_message(payload.message_id)
                await msg.remove_reaction(payload.emoji, payload.member)
                
                message_id_string = str(payload.message_id)
                if message_id_string not in self.last_executions:
                    self.last_executions[message_id_string] = 0

                if (payload.emoji.name == "➡" or payload.emoji.name == "⬅") and time.time() > self.last_executions[message_id_string]+3:
                    qualifier_results_db = read_qualifier_results_db()
                    maps_db = qualifier_results_db["maps"]
                    final_results_db = qualifier_results_db["final_result"]
                    
                    if payload.message_id == final_results_db["message_id"]:
                        max_page = math.ceil(len(final_results_db["final_scores"]) / max_team_per_page )
                        
                        if payload.emoji.name == "➡":
                            page = final_results_db["page"] + 1
                            if page > max_page:
                                page = 1
                        elif payload.emoji.name == "⬅":
                            page = final_results_db["page"] - 1
                            if page < 1:
                                page = max_page
                        final_results_db["page"] = page
                        embed = await self.create_embed_for_final_results(final_results_db["final_scores"], page)
                        await msg.edit(embed=embed)

                    else:
                        for map_id, qualifier_data in maps_db.items():
                            
                            if qualifier_data["qualifier_message_id"] == payload.message_id:
                                max_page = math.ceil(len(qualifier_data["qualifier_scores"]) / max_team_per_page )
                                
                                if payload.emoji.name == "➡":
                                    page = qualifier_data["page"] + 1
                                    if page > max_page:
                                        page = 1
                                elif payload.emoji.name == "⬅":
                                    page = qualifier_data["page"] - 1
                                    if page < 1:
                                        page = max_page
                                qualifier_data["page"] = page
                                embed = await self.create_embed_for_qualifier(maps_db, map_id, page)
                                await msg.edit(embed=embed)
                                break
                    
                    self.last_executions[message_id_string] = time.time()
                    write_qualifier_results_db(qualifier_results_db)

def setup(bot):
    bot.add_cog(Results(bot))
