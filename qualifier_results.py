import discord
import math
from copy import deepcopy
from discord.ext import commands

from database import read_qualifier_results_db, write_qualifier_results_db, get_old_maps, get_settings ,read_tournament_db, read_lobby_db, write_lobby_db
from requester import get_match_info

settings = get_settings()
qualifier_channel_id = 697002041603653663
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
            if team_p2 == user["discord_id"]:
                team["player_2_id"] = user["id"]
                team["player_2_name"] = user["username"]
        team_list.append(team)

    return team_list

def get_message_ids():
    
    qualifier_results_db = read_qualifier_results_db()
    message_list = []
    for map_id, data in qualifier_results_db.items():
        if data["qualifier_message_id"] is not None:
            message_list.append(data["qualifier_message_id"])
    return message_list

class Results(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.message_list = get_message_ids()

    async def create_embed_for_qualifier(self, qualifier_results_db, map_id, page=1):
        
        scores = deepcopy(qualifier_results_db[map_id]["qualifier_scores"])
        scores.sort(key=lambda x: x["player_1_score"]+x["player_2_score"])

        desc_text = ""
        for index, team in enumerate(scores[(page-1)*max_team_per_page : page*max_team_per_page]):

            total_score = team["player_1_score"] + team["player_2_score"]
            desc_text += f"**#{index+1+((page-1)*max_team_per_page)}** - `{team['team_name']}`  ▸Toplam Skor: {'{:,}'.format(total_score)}\n" \
                         f" ▸{team['player_1_name']}: {'{:,}'.format(team['player_1_score'])}  ▸{team['player_2_name']}: {'{:,}'.format(team['player_2_score'])}\n \n"

        mod = qualifier_results_db[map_id]["modpool"]
        color = discord.Color.from_rgb(*settings["mod_colors"][mod])
        url = f"https://osu.ppy.sh/b/{map_id}"

        artist = qualifier_results_db[map_id]["artist"]
        title = qualifier_results_db[map_id]["title"]
        diff_name = qualifier_results_db[map_id]["diff_name"]
            
        embed = discord.Embed(description=desc_text, title=f"{artist} {title}[{diff_name}]",
                                  color=color)
        embed.set_author(name=f"112'nin Corona Turnuvası - Sıralama Sonuçları")
        embed.set_thumbnail(url=settings["mod_icons"][mod])
        embed.url = url
        embed.set_footer(text=f"Page {page} of {math.ceil(len(scores)/max_team_per_page)}")

        return embed


    @commands.command(name="showresult")
    @commands.has_permissions(administrator=True)
    async def show_qualifier_map_results(self, ctx, map_id):
        qualifier_results_db = read_qualifier_results_db()
        
        try:
            embed = await self.create_embed_for_qualifier(qualifier_results_db, map_id)
        except KeyError:
            ctx.send("Aranan map bulunamadı")

        msg = await ctx.send(embed=embed)
        if len(qualifier_results_db[map_id]["qualifier_scores"]) > max_team_per_page:
            await msg.add_reaction("⬅")
            await msg.add_reaction("➡")

        qualifier_results_db[map_id]["qualifier_message_id"] = msg.id
        self.message_list.append(msg.id)
        write_qualifier_results_db(qualifier_results_db)
    
    
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
            channel = discord.utils.get(ctx.message.guild.channels, id=qualifier_channel_id)#add it to settings
            msg = await channel.fetch_message(msg_id)
            
            embed = msg.embeds[0].copy()
            embed.url = mp_link
            await msg.edit(embed=embed)
            
            lobbies[lobby_name]["mp_link"] = mp_link
            write_lobby_db(lobbies)
            

        match_data = get_match_info(mp_link)
        qualifier_results_db = read_qualifier_results_db()
        teams = get_players_with_teams()

        for game in match_data:
            current_teams = deepcopy(teams)
            for scores in game["scores"]:
                for team in current_teams:
                    
                    team["player_1_score"] = 0
                    team["player_2_score"] = 0 
                    write = False
                    if scores["user_id"] == str(team["player_1_id"]):
                        team["player_1_score"] = int(scores["score"])
                        write = True
                    if scores["user_id"] == str(team["player_2_id"]):
                        team["player_2_score"] = int(scores["score"])
                        write = True
                    if write:
                        for index, data in enumerate(qualifier_results_db[game["beatmap_id"]]["qualifier_scores"]):
                            if team["team_name"] == data["team_name"]:
                                del qualifier_results_db[game["beatmap_id"]]["qualifier_scores"][index]
                                break
                            
                        qualifier_results_db[game["beatmap_id"]]["qualifier_scores"].append(team)

            if qualifier_results_db[game["beatmap_id"]]["qualifier_message_id"] is not None:

                channel = discord.utils.get(ctx.message.guild.channels, id=qualifier_channel_id)
                msg = await channel.fetch_message(qualifier_results_db[game["beatmap_id"]]["qualifier_message_id"])

                embed = await self.create_embed_for_qualifier(qualifier_results_db, game["beatmap_id"])
                await msg.edit(embed=embed)
                if len(qualifier_results_db[game["beatmap_id"]]["qualifier_scores"]) > max_team_per_page:
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
                
                if payload.emoji.name == "➡" or payload.emoji.name == "⬅":
                    qualifier_results_db = read_qualifier_results_db()
                    
                    for map_id, qualifier_data in qualifier_results_db.items():
                        
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

                            embed = await self.create_embed_for_qualifier(qualifier_results_db, map_id, page)
                            await msg.edit(embed=embed)
                            
                            qualifier_data["page"] = page
                            write_qualifier_results_db(qualifier_results_db)
                            break

def setup(bot):
    bot.add_cog(Results(bot))
