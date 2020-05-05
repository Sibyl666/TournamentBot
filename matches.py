import discord
from discord.ext import commands
from datetime import datetime, timedelta

from database import get_settings, read_tournament_db, read_match_db, write_match_db, read_mappool_db
from spreadsheet import create_new_match_sheet, get_sheet_data

from backports.datetime_fromisoformat import MonkeyPatch
MonkeyPatch.patch_fromisoformat()



settings = get_settings()
match_channel = 700035482725384285

def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)

def get_team_by_name(team_name):

    tournament_db = read_tournament_db()
    users = tournament_db["users"]
    teams = tournament_db["teams"]
    for team in teams:
        if team["name"] == team_name:
            team_data = {}
            for user in users:
                if team["user1"] == user["discord_id"]:
                    team_data["user_1_name"] = user["username"]
                    team_data["user_1_id"] = user["id"]
                    team_data["user_1_discord_id"] = user["discord_id"]
                elif team["user2"] == user["discord_id"]: 
                    team_data["user_2_name"] = user["username"]
                    team_data["user_2_id"] = user["id"]
                    team_data["user_2_discord_id"] = user["discord_id"]
            return team_data
    return None

def get_beatmaps_in_stage(stage):
    maps_db = read_mappool_db()
    
    maps_in_stage = {}
    mods = {"NM":1, "HD":1, "HR":1, "DT":1, "FM":1, "TB":1}
    for map_id, map_data in maps_db.items():
        if map_data["mappool"] == stage:
            artist = map_data["artist"]
            title = map_data["title"]
            for diff in map_data["beatmaps"]:
                if str(diff["id"]) == map_id:
                    map_data["diff_name"] = diff["version"]
            diff_name = map_data["diff_name"]
            mod = map_data["modpool"]
            map_string = f"{mod}{mods[mod]} | {artist} {title}[{diff_name}]"
            
            maps_in_stage[map_id] = {"mod": mod, "map_string":map_string}
            mods[mod] += 1

    return maps_in_stage

class Matches(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.command(name='showmatches')
    async def show_all_matches(self, ctx):
        
        desc_text = ""
        matches = read_match_db()
        matches.sort(key=lambda x: datetime.fromisoformat(x["date"]))

        print("matches")

        embed = discord.Embed(description=desc_text,
                              color=discord.Color.from_rgb(*settings["tournament_color"]))
        embed.set_author(name="112'nin Corona Turnuvası - Qualifier Lobbies!")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")

        await ctx.send(embed=embed)



    async def create_embed_for_match(self, match_name, match_data):

        match_date = datetime.fromisoformat(match_data["date"])
        date_string = match_date.strftime("%d/%m/%Y - %H:%M, %a")
        
        embed = discord.Embed(
                                  color=discord.Color.from_rgb(*settings["tournament_color"]))
        embed.set_author(name=f"112'nin Corona Turnuvası - Maç {match_name}")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
        
        embed.title = f"{date_string}",
        
        title_text = ""
        team_colored_name = ["Kırmızı Takım", "Mavi Takım"]
        for index, (team_name, team_data) in enumerate(match_data["teams"].items()):
            
            if index == 0:
                title_text += f"{team_name} "
                if team_data["score"] is not None:
                    title_text += f"{team_data['score']}"
                title_text += " | "
            elif index == 1:
                if team_data["score"] is not None:
                    title_text += f"{team_data['score']}"
                title_text += f" {team_name}"
            
            field_text = f"__**{team_name}**__\n" \
                         f"{team_data['user_1_name']}, {team_data['user_2_name']} \n" \
                         
            if team_data["roll"] is not None:
                field_text += f"▸Roll: {team_data['roll']}\n"

            if len(team_data["bans"]) > 0 :
                bans_text = ' '.join(team_data['bans'])
                field_text += f"▸Bans: {bans_text}" 

            embed.add_field(name=team_colored_name[index], value=field_text, inline=True)    

        embed.add_field(name ='\u200b' , value='\u200b',  inline=True )
        embed.title = title_text
        embed.description = f"{date_string}"

        if match_data["ff_message"] is not None:
            embed.description += "\n" + match_data["ff_message"]
        if match_data["mp_link"] is not None:
            embed.url = match_data["mp_link"]
        if match_data["referee"] is not None:
            referee = match_data["referee"]
            embed.add_field(name="Hakem:", value=f"<@{referee['discord_id']}>",inline=True)
        if match_data["streamer"] is not None:
            streamer = match_data["streamer"]
            embed.add_field(name="Yayıncı:", value=f"<@{streamer['discord_id']}>", inline=True)
        if len(embed.fields) > 4:
            embed.add_field(name ='\u200b' , value='\u200b',  inline=True)

        return embed


    @commands.command(name='matchadd')
    @commands.has_permissions(administrator=True)
    async def add_match(self, ctx, match_name, team_1_name, team_2_name, pool, *time):
        """
        Add new match
        time: Time of the qualifier match in format (dd/mm HH:MM)
        """

        pools = ["W1", "W2", "W3","W4"]
        if pool not in pools:
            await ctx.send(f"`{pool}` yok.")
            return

        matches = read_match_db()
        if match_name in matches.keys():
            await ctx.send(f"`{match_name}` adlı maç zaten var.")
            return

        team_1_data = get_team_by_name(team_1_name)
        if team_1_data is None:
            await ctx.send(f"`{team_1_name}` adlı takım bulunamadı.")
            return

        team_2_data = get_team_by_name(team_2_name)
        if team_2_data is None:
            await ctx.send(f"`{team_2_name}` adlı takım bulunamadı.")
            return

        default_values = {"score": None, "roll": None, "bans":[]}
        team_1_data.update(default_values)
        team_2_data.update(default_values)
        teams = {team_1_name:team_1_data, team_2_name:team_2_data}

        time = " ".join(time)
        match_date = datetime.strptime(time, "%d/%m %H:%M")
        match_date = match_date.replace(year=2020)

        matches[match_name] = {"date": match_date.isoformat(), "name": match_name, "pool":pool, "teams": teams, "sheet_id":None, "mp_link":None, "referee":None, "streamer":None, "ff_message":None}

        embed = await self.create_embed_for_match(match_name, matches[match_name])
        channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
        msg = await channel.send(embed=embed)
        matches[match_name]["message_id"] = msg.id

        write_match_db(matches)
        await ctx.send(f"`{match_name}` adlı maç oluşturuldu.")

        

    @commands.command(name='matchrm')
    @commands.has_permissions(administrator=True)
    async def remove_match(self, ctx, match_name):
        """
        Remove match
        match_name: Silinecek maçın adı
        """
        matches = read_match_db()
        deleted = matches.pop(match_name, None)
        if deleted is None:
            await ctx.send(f"`{match_name}` adında bir maç yok.")
            return

        msg_id = deleted["message_id"]
        channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
        msg = await channel.fetch_message(msg_id)
        await msg.delete()
        write_match_db(matches)
        await ctx.send(f"`{match_name}` adlı maç sildindi.")


    @commands.command(name='refmatchjoin')
    @commands.has_role("Hakem")
    async def register_referee_to_match(self, ctx, match_name):
        """
        Hakemlik yapmak istediğiniz maçlara kaydolun.
        match_name: Kaydolmak istediğiniz maçın adı
        """
        matches = read_match_db()

        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return

        if matches[match_name]["referee"] != None:
            await ctx.send(f"`{match_name}` maçına zaten bir hakem kayıtlı.")
            return

        referee_data = {"name": ctx.author.name, "discord_id": ctx.author.id}
        matches[match_name]["referee"] = referee_data
        
        msg_id = matches[match_name]["message_id"]
        channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
        msg = await channel.fetch_message(msg_id)
        embed = await self.create_embed_for_match(match_name, matches[match_name])
        await msg.edit(embed=embed)

        write_match_db(matches)
        await ctx.send(f"`{ctx.author.name}`, `{match_name}` maçına hakem olarak katıldı.")

    @commands.command(name='refmatchleave')
    @commands.has_role("Hakem")
    async def remove_referee_from_match(self, ctx, match_name):
        """
        Hakemliği bırakmak istediğiniz maçtan çıkın.
        match_name: Çıkmak istediğiniz maçın adı
        """
        matches = read_match_db()
        
        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return
        
        if matches[match_name]["referee"]["discord_id"] != ctx.author.id:
            await ctx.send(f"`{match_name}` adındaki maçta hakem sen değilsin.")
            return
        else:
            matches[match_name]["referee"] = None
            
            msg_id = matches[match_name]["message_id"]
            channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
            msg = await channel.fetch_message(msg_id)
            embed = await self.create_embed_for_match(match_name, matches[match_name])
            await msg.edit(embed=embed)
           
            write_match_db(matches)
            await ctx.send(f"`{ctx.author.name}`, `{match_name}` maçındaki hakemlikten ayrıldı.")


    @commands.command(name='streamermatchjoin')
    @commands.has_role("Yayıncı")
    async def register_streamer_to_match(self, ctx, match_name, in_game_name):
        """
        Yayın yapmak istediğiniz maçlara kaydolun.
        match_name: Kaydolmak istediğiniz maçın adı
        in_game_name: osu!'daki adın
        """
        matches = read_match_db()

        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return

        if matches[match_name]["streamer"] != None:
            await ctx.send(f"`{match_name}` maçına zaten bir yayıncı kayıtlı.")
            return

        streamer_data = {"name": ctx.author.name, "discord_id": ctx.author.id, "osu_name": in_game_name}
        matches[match_name]["streamer"] = streamer_data
        
        msg_id = matches[match_name]["message_id"]
        channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
        msg = await channel.fetch_message(msg_id)
        embed = await self.create_embed_for_match(match_name, matches[match_name])
        await msg.edit(embed=embed)

        write_match_db(matches)
        await ctx.send(f"`{ctx.author.name}`, `{match_name}` maçına yayıncı olarak katıldı.")

        
    @commands.command(name='streamermatchleave')
    @commands.has_role("Yayıncı")
    async def remove_streamer_from_match(self, ctx, match_name):
        """
        Yayıncılığı bırakmak istediğiniz maçtan çıkın.
        match_name: Çıkmak istediğiniz maçın adı
        """
        matches = read_match_db()
        
        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return
        
        if matches[match_name]["streamer"]["discord_id"] != ctx.author.id:
            await ctx.send(f"`{match_name}` adındaki maçta yayıncı sen değilsin.")
            return
        else:
            matches[match_name]["streamer"] = None
            
            msg_id = matches[match_name]["message_id"]
            channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
            msg = await channel.fetch_message(msg_id)
            embed = await self.create_embed_for_match(match_name, matches[match_name])
            await msg.edit(embed=embed)
           
            write_match_db(matches)
            await ctx.send(f"`{ctx.author.name}`, `{match_name}` maçındaki yayıncılıktan ayrıldı.")

    @commands.command(name='creatermatchefsheet')
    @commands.has_role("Hakem")
    async def create_ref_sheet(self, ctx, match_name):
        """
        Maçı yönetmek için hakem sheeti oluşturun
        match_name: Sheet açmak istediğiniz maçın adı
        """
        matches = read_match_db()

        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return
        
        if matches[match_name]["referee"]["discord_id"] != ctx.author.id:
            await ctx.send(f"`{match_name}` adındaki maçta hakem sen değilsin.")
            return
        else:
            msg = await ctx.send(f"Hakem Sheet oluşturuluyor!")
            maps = get_beatmaps_in_stage(matches[match_name]["pool"])
            url, sheet_id = create_new_match_sheet(match_name, matches[match_name], maps)
            matches[match_name]["sheet_id"] = sheet_id
            write_match_db(matches)
            await msg.delete()
            await ctx.send(f"Hakem Sheet oluşturuldu! Linkten ulaşabilirsin!\n" \
                           f"<{url}>")

    
    @commands.command(name='updatematch')
    @commands.has_role("Hakem")
    async def get_data_from_sheet(self, ctx, match_name):
        """
        Oluşturduğunuz sheetten detayları alıp maçı güncelleyin.
        match_name: Güncellemek istediğiniz maçın adı
        """
        matches = read_match_db()

        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return
        
        if matches[match_name]["referee"]["discord_id"] != ctx.author.id:
            await ctx.send(f"`{match_name}` adındaki maçta hakem sen değilsin.")
            return
        else:
            start_msg = await ctx.send(f"Bilgiler alınıyor!")
            
            mp_link, new_data = get_sheet_data(matches[match_name]["sheet_id"])
            matches[match_name]["mp_link"] = mp_link
            for key, data in new_data.items():
                matches[match_name]["teams"][key].update(data)

            msg_id = matches[match_name]["message_id"]
            channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
            msg = await channel.fetch_message(msg_id)
            embed = await self.create_embed_for_match(match_name, matches[match_name])
            await msg.edit(embed=embed)
            write_match_db(matches)
            await start_msg.delete()
            await ctx.send("Bilgiler başarıyla alındı.")


    @commands.command(name='declareff')
    @commands.has_role("Hakem")
    async def declare_ff(self, ctx, match_name, team, message=None):
        """
        FF biten maçları güncerlleyin
        match_name: Maçın adı
        team: Kazanan takımın adı
        message: Açıklama mesajı. tırnak içinde yazın ("")
        """
        matches = read_match_db()
        
        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return
    

        teams = list(matches[match_name]["teams"].keys())
        if team not in teams:
            await ctx.send(f"**{team}** takımı `{match_name}` maçında değil. Bu maçtaki takımlar: `{teams[0]}`, `{teams[1]}`")
            return

        else:
            for team_name, team_data in matches[match_name]["teams"].items():
                if team_name == team:
                    team_data["score"] = 1
                else:
                    team_data["score"] = "ff"

            matches[match_name]["ff_message"] = message

            msg_id = matches[match_name]["message_id"]
            channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
            msg = await channel.fetch_message(msg_id)
            embed = await self.create_embed_for_match(match_name, matches[match_name])
            await msg.edit(embed=embed)

            write_match_db(matches)
            await ctx.send(f"{team} kazandı sayıldı. Eğer yanlış yazdıysanız komutu tekrar kullanarak düzeltebilirsiniz.")


    @commands.command(name='pingmatch')
    @commands.has_role("Hakem")
    async def ping_match(self, ctx, match_name):
        """
        Maçtaki oyuncuları pingleyin
        match_name: Pinlemek istediğiniz odanın adı
        """
        matches = read_match_db()
        
        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return
        
        if matches[match_name]["referee"]["discord_id"] != ctx.author.id:
            await ctx.send(f"`{match_name}` adındaki maçta hakem sen değilsin.")
            return
        else:
            teams = matches[match_name]["teams"]
            msg_team_part = ""
            for team_name, team_data in teams.items():
                msg_team_part += f" `{team_name}` - <@{team_data['user_1_discord_id']}> , <@{team_data['user_2_discord_id']}>"
                
            await ctx.send(f"Hakem {ctx.author.mention} , `{match_name}` adlı lobiyi pingliyor:\n{msg_team_part}")


    @commands.command(name='newtime')
    @commands.has_permissions(administrator=True)
    async def change_match_time(self, ctx, match_name, *time):
        """
        Maç saatini değiştirin
        match_name: Değiştirmek istediğiniz odanın adı.
        """
        matches = read_match_db()
        
        if match_name not in matches:
            await ctx.send(f"`{match_name}` adında bir maç yok..")
            return
      
        else:
            time = " ".join(time)
            match_date = datetime.strptime(time, "%d/%m %H:%M")
            match_date = match_date.replace(year=2020)

            matches[match_name]["date"] = match_date.isoformat()

            msg_id = matches[match_name]["message_id"]
            channel = discord.utils.get(ctx.message.guild.channels, id=match_channel)
            msg = await channel.fetch_message(msg_id)
            embed = await self.create_embed_for_match(match_name, matches[match_name])
            await msg.edit(embed=embed)

            write_match_db(matches)

            date_string = match_date.strftime("%d/%m/%Y - %H:%M, %a")
            
            text = f"`{match_name}` maçının zamanı değiştirildi! Yeni zaman: `{date_string}`.\n"
            
            if matches[match_name]["referee"] is not None:
                referee_id = matches[match_name]["referee"]["discord_id"]
                text += f"<@{referee_id}> maça yeni saatinde hakemlik yapamayacaksan `?refmatchleave {match_name}` komutuyla maçı bırakabilirsin."

            
            await ctx.send(text)


def setup(bot):
    bot.add_cog(Matches(bot))