import discord
from copy import deepcopy
from discord.ext import commands

from database import read_mappool_db, write_mappool_db, get_old_maps, get_settings ,read_tournament_db, read_lobby_db, write_lobby_db
from requester import get_match_info

settings = get_settings()
qualifier_channel_id = 693913004957368353

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
 

class Results(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def create_embed_for_qualifier(self,ctx,mappool_db,map_id):
        try:
            scores = deepcopy(mappool_db["map_id"]["qualifier_scores"])
        except KeyError:
            await ctx.send(f"Aranan map bulunamadı.")
            return

        scores.sort(key=lambda x: x["player_1_score"]+x["player_2_score"])
        desc_text = ""
        for index, team in enumerate(scores):

            team_name = team["team_name"]
            total_score = team["player_1_score"] + team["player_2_score"]
            text += f"#{index+1}- `{team_name}` - {total_score}"

        mod = mappool_db["map_id"]["modpool"]
        color = discord.Color.from_rgb(*settings["mod_colors"][mod])
        url = f"https://osu.ppy.sh/b/{map_id}"

        artist = mappool_db["map_id"]["artist"]
        title = mappool_db["map_id"]["title"]
        for diff in mappool_db["map_id"]["beatmaps"]:
            if diff["id"] == map_id:
                diff_name = diff["version"]


        embed = discord.Embed(description=desc_text, title=f"{artist} - {title} - {diff_name}",
                                  color=color)
        embed.set_author(name=f"112'nin Corona Turnuvası - Sıralama Sonuçları")
        embed.set_thumbnail(
            url=settings["mod_icons"][mod])
        embed.url = url

        return embed


    @commands.command(name="showresult")
    @commands.has_permissions(administrator=True)
    async def show_qualifier_map_results(self, ctx, map_id):
        mappool_db = read_mappool_db()
        
        embed = self.create_embed_for_qualifier(ctx, mappool_db, map_id)
        msg = await ctx.send(embed=embed)
        
        mappool_db["map_id"]["qualifier_message_id"] = msg.id

        write_mappool_db(mappool_db)
    
    
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
            channel = discord.utils.get(ctx.message.guild.channels, id=695995975189135430)#add it to settings
            msg = await channel.fetch_message(msg_id)
            
            embed = msg.embeds[0].copy()
            embed.url = mp_link
            await msg.edit(embed=embed)
            
            lobbies[lobby_name]["mp_link"] = mp_link
            write_lobby_db(lobbies)
            

        match_data = get_match_info(mp_link)
        mappool_db = read_mappool_db()
        teams = get_players_with_teams()

        for game in match_data:
            current_teams = deepcopy(teams)
            update_list = []
            for scores in game["scores"]:
                for team in current_teams:
                    if scores["user_id"] == team["player_1_id"]:
                        team["player_1_score"] = int(scores["score"])
                    if scores["user_id"] == team["player_2_id"]:
                        team["player_2_score"] = int(scores["score"])
                update_list.append(update_list)

            mappool_db[game["beatmap_id"]]["qualifier_scores"] += update_list


            if mappool_db[game["beatmap_id"]]["qualifier_message_id"] is not None:

                channel = discord.utils.get(ctx.message.guild.channels, id=qualifier_channel_id)
                msg = await channel.fetch_message(msg_id)
                
                embed = self.create_embed_for_qualifier(ctx, mappool_db, game["beatmap_id"])
                await msg.edit(embed=embed)            


        write_mappool_db(mappool_db)
        await ctx.send(f"`{ctx.author.name}`, `{lobby_name}` lobisine mp link eklendi.")


def setup(bot):
    bot.add_cog(Results(bot))
