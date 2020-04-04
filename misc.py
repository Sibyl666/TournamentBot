import discord
from discord.ext import commands

from database import read_tournament_db, get_settings

settings = get_settings()


class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx, osu_username):
        """
        osu! nicki verilen oyuncuyu pingler
        osu_username: Pinglemek istediğiniz oyuncunun osu!'daki ismi
        """
        db = read_tournament_db()

        for user in db["users"]:
            if osu_username.lower() == user["username"].lower():
                discord_user = discord.utils.get(ctx.guild.members, id=user["discord_id"])
                await ctx.send(discord_user.mention)
                return


def setup(bot):
    bot.add_cog(Misc(bot))
