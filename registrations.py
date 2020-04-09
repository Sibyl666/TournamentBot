import discord
from discord.ext import commands

from database import read_tournament_db, write_tournament_db, get_settings
from requester import get_user_info
from rank_calculations import get_teammate_rank
from registration_check import check_registration

settings = get_settings()


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


def disband_team(team):
    db = read_tournament_db()
    if team in db["teams"]:
        db["teams"].remove(team)
    else:
        return -1
    write_tournament_db(db)
    return 0


class Registrations(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    async def remove_user_role(self, discord_id):
        guild = self.bot.get_guild(402213530599948299)
        player_role = discord.utils.get(guild.roles, id=693574523324203009)
        discord_user = discord.utils.get(guild.members, id=discord_id)
        if player_role in discord_user.roles:
            await discord_user.remove_roles(player_role)

        return

    @commands.command(name='register')
    @commands.has_permissions(administrator=True)
    async def register_tourney(self, ctx, osu_user1):
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
                await ctx.send(
                    f"Turnuvaya `{uname}` adıyla kayıt olunmuş. Turnuvadan ayrılmak için: `{settings['prefix']}leave`")
                return

        user1_info = get_user_info(osu_user1)

        user1_info["discord_id"] = ctx.author.id
        teammate_min_rank = get_teammate_rank(user1_info["statistics"]["pp_rank"])

        db["users"].append(user1_info)

        write_tournament_db(db)

        guild = self.bot.get_guild(402213530599948299)
        player_role = discord.utils.get(guild.roles, id=693574523324203009)
        if player_role not in ctx.author.roles:
            await ctx.author.add_roles(player_role)

        await ctx.send(f"`{osu_user1}` başarıyla turnuvaya katıldın! Devam edebilmek için bir takım kurman gerekiyor:\n"
                       f"Kullanım: `{settings['prefix']}team @oyuncu takım_ismi`\n Ex. `{settings['prefix']}team @heyronii Yokediciler`\n"
                       f"Beraber katılabileceğin takım arkadaşın {teammate_min_rank:0d}+ rank olabilir.")
        return

    @commands.command(name='kick')
    @commands.has_permissions(administrator=True)
    async def kick_player(self, ctx, osu_username):
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
            await self.remove_user_role(discord_id)
            await ctx.send(f"`{osu_username}` turnuvadan ayrıldı, tekrar görüşmek üzere.")

        if ret["disbanded"]:
            team_name = info["team_name"]
            p2_discord = info["p2_discord"]
            await ctx.send(f"`{team_name}` takımı bozuldu... <@{p2_discord}>")

        return

    @commands.command(name='leave')
    @commands.has_permissions(administrator=True)
    async def remove_user(self, ctx):
        """
        Komutu kullanan kişiyi turnuvadan çıkarır.
        İçinde bulunduğu takım varsa, bozulur.
        """
        ret, info = remove_user_from_tournament(ctx.author.id)

        if ret is None:
            await ctx.send(f"{ctx.author.mention} turnuvaya kayıtlı değilsin...")

        if ret["removed"]:
            osu_username = info["osu_username"]
            await self.remove_user_role(ctx.author.id)
            await ctx.send(f"`{osu_username}` turnuvadan ayrıldı, tekrar görüşmek üzere.")

        if ret["disbanded"]:
            team_name = info["team_name"]
            p2_discord = info["p2_discord"]
            await ctx.send(f"`{team_name}` takımı bozuldu... <@{p2_discord}>")

        return


def setup(bot):
    bot.add_cog(Registrations(bot))
