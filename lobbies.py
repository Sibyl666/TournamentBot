import discord
from discord.ext import commands
from datetime import datetime, timedelta
from database import get_settings, read_lobby_db, write_lobby_db, read_tournament_db
from faker import Faker
from backports.datetime_fromisoformat import MonkeyPatch
MonkeyPatch.patch_fromisoformat()


settings = get_settings()

fake = Faker('tr_TR')

LOBBY_TEAM_LIMIT = 8
test = 695995314976325662
servis = 695995975189135430
lobi_channel_announce_id = 693913004957368353

def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def is_user_captain(author_id, users):
    user_found = False
    add_this_team = None
    for team in users["teams"]:
        if team["user1"] == author_id:
            user_found = True
            add_this_team = team

    if not user_found:
        return

    return add_this_team


class Lobbies(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='nextlobby')
    async def show_next_lobby(self, ctx):
        """
        Sıradaki lobiyi gösterir.        
        """
        lobbies = read_lobby_db()
        lobby_list = [{"name": k, "date": datetime.fromisoformat(v["date"]), "teams": v["teams"], "referee_discord_id":v["referee_discord_id"], "mp_link":v["mp_link"]}
                      for k, v in lobbies.items()]
        lobby_list.sort(key=lambda x: x["date"])

        for lobby in lobby_list:
            date = lobby["date"]
            name = lobby["name"]
            teams = lobby["teams"]
            
            remains = date - datetime.now()
            if remains.total_seconds() > 0:
                desc_text = ""
                for team_name, players in teams.items():
                    desc_text += f"▸**{team_name}** - {players[0][1]}, {players[1][1]}\n"

                rem_time = strfdelta(remains, "{days} days {hours} hours {minutes} minutes")
                date_string = date.strftime("%d/%m/%Y - %H:%M, %a")
                embed = discord.Embed(description=desc_text, title=f"{date_string}",
                                      color=discord.Color.from_rgb(*settings["tournament_color"]))
                embed.set_author(name=f"112'nin Corona Turnuvası - Qualifier Lobby {name}")
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
                embed.set_footer(text=f"Remaining time: {rem_time}")

                if lobby["referee_discord_id"] != "":
                    embed.insert_field_at(index= 0, name="Hakem:", value=f"<@{lobby['referee_discord_id']}>", inline=True)
                if lobby["mp_link"] != "":
                    embed.url = lobby["mp_link"]


                await ctx.send(embed=embed)
                break
        return

    @commands.command(name='lobbies')
    async def show_all_lobbies(self, ctx):
        """
        Shows all of the qualifier lobbies
        """
        desc_text = ""
        lobbies = read_lobby_db()
        lobby_list = [{"name": k, "date": datetime.fromisoformat(v["date"]), "teams": v["teams"]} for k, v in lobbies.items()]
        lobby_list.sort(key=lambda x: x["date"])

        for lobby in lobby_list:
            name = lobby["name"]
            date = lobby["date"].strftime("%d/%m/%Y - %H:%M, %a")
            desc_text += f"▸**{name}** - {date}"
            if len(lobby["teams"]) == 8:
                desc_text += "** (FULL!)**\n"
            else:
                desc_text += f" {len(lobby['teams'])}/8\n"

        embed = discord.Embed(description=desc_text,
                              color=discord.Color.from_rgb(*settings["tournament_color"]))
        embed.set_author(name="112'nin Corona Turnuvası - Qualifier Lobbies!")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")

        await ctx.send(embed=embed)
        return

    @commands.command(name='lobbyadd')
    @commands.has_permissions(administrator=True)
    async def add_lobby(self, ctx, *time):
        """
        Add new qualifier lobby
        time: Time of the qualifier lobby in format (dd/mm HH:MM)
        """
        time = " ".join(time)

        lobby_date = datetime.strptime(time, "%d/%m %H:%M")
        lobby_date = lobby_date.replace(year=2020)
        date_string = lobby_date.strftime("%d/%m/%Y - %H:%M, %a")
        now = datetime.now()
        rem_time = strfdelta(lobby_date - now, "{days} days {hours} hours {minutes} minutes")

        lobbies = read_lobby_db()
        lobby_name = fake.first_name_female()
        while lobby_name in lobbies.keys():
            lobby_name = fake.first_name_female()

        embed = discord.Embed(title=f"Lobby Name: {lobby_name}", description=f"{date_string}",
                              color=discord.Color.from_rgb(*settings["tournament_color"]))
        embed.set_author(name="112'nin Corona Turnuvası - Lobby Created!")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
        #embed.set_footer(text=f"Remaining time: {rem_time}")

        channel = discord.utils.get(ctx.message.guild.channels, id=lobi_channel_announce_id)

        msg = await channel.send(embed=embed)

        lobbies[lobby_name] = {"date": lobby_date.isoformat(), "name": lobby_name, "teams": {}, "msg_id": msg.id, "mp_link":"", "referee":"", "referee_discord_id":""}
        write_lobby_db(lobbies)

        return

    @commands.command(name='lobbyrm')
    @commands.has_permissions(administrator=True)
    async def remove_lobby(self, ctx, name):
        """
        Remove lobby from qualifier lobbies
        name: Lobby name to remove
        """
        lobbies = read_lobby_db()
        ret = lobbies.pop(name, None)
        if ret is None:
            await ctx.send(f"There's no lobby named `{name}`.")
            return

        msg_id = ret["msg_id"]
        channel = discord.utils.get(ctx.message.guild.channels, id=lobi_channel_announce_id)
        msg = await channel.fetch_message(msg_id)
        await msg.delete()
        write_lobby_db(lobbies)
        await ctx.send(f"Deleted `{name}` from the lobbies.")
        return

    @commands.command(name='lobbyregister')
    @commands.has_role("Oyuncu")
    async def register_player_to_lobby(self, ctx, lobby_name):
        """
        Qualifier lobisine kaydolun
        lobby: Kaydolmak istediğiniz lobinin ismi
        """

        users = read_tournament_db()
        author_id = ctx.author.id
        team = is_user_captain(author_id, users)
        team_name = team["name"]

        if team is None:
            await ctx.send("Takımın yok veya takım kaptanı değilsin...")
            return

        lobbies = read_lobby_db()

        if lobby_name not in lobbies:
            await ctx.send(f"`{lobby_name}` adında bir lobi yok..")
            return

        if len(lobbies[lobby_name]["teams"]) >= LOBBY_TEAM_LIMIT:
            await ctx.send(f"`{lobby_name}` isimli lobi dolu.")
            return

        for name, lobby in lobbies.items():
            if team_name in lobby["teams"]:
                await ctx.send(f"Bulunduğun takım `{name}` lobisinde kayıtlı gözüküyor.\n"
                               f"Lobini değişirmek için önce lobiden ayrılmalısın. (`?lobbyleave`)")
                return

        for user in users["users"]:
            if user["discord_id"] == ctx.author.id:
                osu_user1 = user["username"]
        for user in users["users"]:
            if user["discord_id"] == team["user2"]:
                osu_user2 = user["username"]

        user1 = [team["user1"], osu_user1]
        user2 = [team["user1"], osu_user2]
        team_players = [user1, user2]
        lobbies[lobby_name]["teams"][team_name] = team_players
        lobby_teams = lobbies[lobby_name]["teams"]
        lobby_date = datetime.fromisoformat(lobbies[lobby_name]["date"])

        desc_text = ""
        for team_name, players in lobby_teams.items():
            desc_text += f"▸**{team_name}** - {players[0][1]}, {players[1][1]}\n"

        date_string = lobby_date.strftime("%d/%m/%Y - %H:%M, %a")
        embed = discord.Embed(description=desc_text, title=f"{date_string}",
                              color=discord.Color.from_rgb(*settings["tournament_color"]))
        embed.set_author(name=f"112'nin Corona Turnuvası - Qualifier Lobby {lobby_name}")
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
        

        if lobbies[lobby_name]["referee"] != "":
            embed.insert_field_at(index= 0, name="Hakem:", value=f"<@{lobbies[lobby_name]['referee_discord_id']}>", inline=True)
        if lobbies[lobby_name]["mp_link"] != "":
            embed.url = lobbies[lobby_name]["mp_link"]

        msg_id = lobbies[lobby_name]["msg_id"]
        channel = discord.utils.get(ctx.message.guild.channels, id=lobi_channel_announce_id)
        msg = await channel.fetch_message(msg_id)
        await msg.edit(embed=embed)

        write_lobby_db(lobbies)

        await ctx.send(f"`{team_name}` takımını `{lobby_name}` adlı lobiye ekledim!")
        return

    @commands.command(name='lobbyleave')
    @commands.has_role("Oyuncu")
    async def remove_player_from_lobby(self, ctx):
        """
        Katıldığınız Qualifier lobisinden çıkın.
        """
        users = read_tournament_db()
        author_id = ctx.author.id
        team = is_user_captain(author_id, users)
        team_name = team["name"]

        if team is None:
            await ctx.send("Takımın yok veya takım kaptanı değilsin...")
            return

        lobbies = read_lobby_db()

        old_lobby = None
        for k, v in lobbies.items():
            if team_name in v["teams"]:
                old_lobby = k

        if old_lobby is not None:
            team_to_add = lobbies[old_lobby]["teams"].pop(team_name)
        else:
            await ctx.send("Henüz bir lobiye kayıtlı değilsin. `?lobbyregister` komutunu kullan.")
            return

        old_lobby_teams = lobbies[old_lobby]["teams"]
        old_lobby_date = datetime.fromisoformat(lobbies[old_lobby]["date"])
        old_lobby_name = lobbies[old_lobby]["name"]
        old_desc_text = ""
        for team_name, players in old_lobby_teams.items():
            old_desc_text += f"▸**{team_name}** - {players[0][1]}, {players[1][1]}\n"

        old_date_string = old_lobby_date.strftime("%d/%m/%Y - %H:%M, %a")
        old_embed = discord.Embed(description=old_desc_text, title=f"{old_date_string}",
                                  color=discord.Color.from_rgb(*settings["tournament_color"]))
        old_embed.set_author(name=f"112'nin Corona Turnuvası - Qualifier Lobby {old_lobby_name}")
        old_embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")
        
        if lobbies[old_lobby_name]["referee"] != "":
            old_embed.insert_field_at(index= 0, name="Hakem:", value=f"<@{lobbies[old_lobby_name]['referee_discord_id']}>", inline=True)
        if lobbies[old_lobby_name]["mp_link"] != "":
            old_embed.url = lobbies[old_lobby_name]["mp_link"]

        old_msg_id = lobbies[old_lobby]["msg_id"]
        channel = discord.utils.get(ctx.message.guild.channels, id=lobi_channel_announce_id)
        old_msg = await channel.fetch_message(old_msg_id)
        await old_msg.edit(embed=old_embed)

        write_lobby_db(lobbies)
        await ctx.send(f"`{team_name}` takımı `{old_lobby}` lobisinden ayrıldı.")
        return


    @commands.command(name='refregister')
    @commands.has_role("Hakem")
    async def register_referee_to_lobby(self, ctx, lobby_name):
        """
        Hakemlik yapmak istediğiniz odalara kaydolun.
        lobby_name: Kaydolmak istediğiniz odanın adı
        """
        lobbies = read_lobby_db()

        if lobby_name not in lobbies:
            await ctx.send(f"`{lobby_name}` adında bir lobi yok..")
            return

        if lobbies[lobby_name]["referee"] != "":
            await ctx.send(f"`{lobby_name}`'de zaten bir hakem kayıtlı.")
            return

        lobbies[lobby_name]["referee"] = ctx.author.name
        lobbies[lobby_name]["referee_discord_id"] = ctx.author.id
        
        msg_id = lobbies[lobby_name]["msg_id"]
        channel = discord.utils.get(ctx.message.guild.channels, id=lobi_channel_announce_id)
        msg = await channel.fetch_message(msg_id)
        
        embed = msg.embeds[0].copy()
        embed.insert_field_at(index= 0, name="Hakem:", value=f"<@{ctx.author.id}>", inline=True)
        await msg.edit(embed=embed)

        write_lobby_db(lobbies)
        await ctx.send(f"`{ctx.author.name}`, `{lobby_name}` lobisine hakem olarak katıldı.")

    @commands.command(name='refleave')
    @commands.has_role("Hakem")
    async def remove_referee_to_lobby(self, ctx, lobby_name):
        """
        Hakemliği bırakmak istediğiniz odadan çıkın.
        lobby_name: Çıkmak istediğiniz odanın adı
        """
        lobbies = read_lobby_db()
        
        if lobby_name not in lobbies:
            await ctx.send(f"`{lobby_name}` adında bir lobi yok..")
            return
        
        if lobbies[lobby_name]["referee_discord_id"] != ctx.author.id:
            await ctx.send(f"`{lobby_name}` adındaki lobide hakem sen değilsin.")
            return
        else:
            lobbies[lobby_name]["referee"] = ""
            lobbies[lobby_name]["referee_discord_id"] = ""
            
            msg_id = lobbies[lobby_name]["msg_id"]
            channel = discord.utils.get(ctx.message.guild.channels, id=lobi_channel_announce_id)
            msg = await channel.fetch_message(msg_id)
        
            embed = msg.embeds[0].copy()
            embed.remove_field(0)
            await msg.edit(embed=embed)

            write_lobby_db(lobbies)
            await ctx.send(f"`{ctx.author.name}`, `{lobby_name}` lobisindeki hakemlikten ayrıldı.")

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
            await ctx.send(f"`{lobby_name}` adındaki lobide hakem sen değilsin.")
            return
        else:
            msg_id = lobbies[lobby_name]["msg_id"]
            channel = discord.utils.get(ctx.message.guild.channels, id=lobi_channel_announce_id)
            msg = await channel.fetch_message(msg_id)
            
            embed = msg.embeds[0].copy()
            embed.url = mp_link
            await msg.edit(embed=embed)
            
            lobbies[lobby_name]["mp_link"] = mp_link
            write_lobby_db(lobbies)
            await ctx.send(f"`{ctx.author.name}`, `{lobby_name}` lobisine mp link eklendi.")


def setup(bot):
    bot.add_cog(Lobbies(bot))
