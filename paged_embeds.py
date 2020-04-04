import discord
import asyncio
import math
from copy import deepcopy
from discord.ext import commands

from database import read_tournament_db, get_settings
from rank_calculations import get_teammate_rank
from registration_check import check_registration

settings = get_settings()


def get_teams_desc(data):
    desc_lines = []
    show_data = data["teams"]
    for team_no, data_point in enumerate(show_data):
        team_name = data_point["name"]
        team_p1 = data_point["user1"]
        team_p2 = data_point["user2"]

        for user in data["users"]:
            if team_p1 == user["discord_id"]:
                team_p1_uname = user["username"]
            if team_p2 == user["discord_id"]:
                team_p2_uname = user["username"]

        desc_lines += [f"#{team_no + 1}: `{team_name}` - {team_p1_uname} & {team_p2_uname}"]

    return desc_lines


def get_player_desc(data):
    desc_lines = []
    show_data = data["users"]
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
                desc_lines += [f"#{user_no + 1} - `{username}` - #{user_rank} - `{team_name}`"]
                break
        if not has_team:
            desc_lines += [f"**#{user_no + 1} - `{username}` - #{user_rank}**"]

    return desc_lines


class Paged_Embed(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.result_per_page = 16

    def get_page_as_string(self, line_list, page_no):

        page_lines = line_list[(page_no - 1) * self.result_per_page: page_no * self.result_per_page]
        return "\n".join(page_lines)

    def create_embed(self, desc_text, fixed_fields):

        embed = discord.Embed(description=desc_text, color=discord.Color.from_rgb(*settings["tournament_color"]))
        embed.set_author(name=fixed_fields["author_name"])
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/520370557531979786/693448457154723881/botavatar.png")

        return embed

    async def send_and_control_pages(self, ctx, lines, fixed_fields):

        page_no = 1
        max_page = math.ceil(len(lines) / self.result_per_page)

        page_string = self.get_page_as_string(lines, page_no)
        embed = self.create_embed(page_string, fixed_fields)

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
                    res, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check_react)
                except asyncio.TimeoutError:
                    return await msg.clear_reactions()

                if user != ctx.message.author:
                    pass
                elif '⬅' in str(res.emoji):
                    page_no -= 1
                    if page_no < 1:
                        page_no = max_page

                    page_string = self.get_page_as_string(lines, page_no)
                    embed2 = self.create_embed(page_string, fixed_fields)
                    embed2.set_footer(text=f"Page {page_no} of {max_page}")

                    await msg.clear_reactions()
                    await msg.edit(embed=embed2)

                elif '➡' in str(res.emoji):
                    page_no += 1
                    if page_no > max_page:
                        page_no = 1

                    page_string = self.get_page_as_string(lines, page_no)
                    embed2 = self.create_embed(page_string, fixed_fields)
                    embed2.set_footer(text=f"Page {page_no} of {max_page}")

                    await msg.clear_reactions()
                    await msg.edit(embed=embed2)

    @commands.command(name='players')
    async def show_registered_players(self, ctx):
        """
        Turnuvaya kayıtlı oyuncuları gösterir.
        """
        data = read_tournament_db()
        desc_lines = get_player_desc(data)
        fixed_fields = {"author_name": "112'nin Corona Turnuvası Oyuncu Listesi"}

        await self.send_and_control_pages(ctx, desc_lines, fixed_fields)

    @commands.command(name='teams')
    async def show_registered_teams(self, ctx):
        """
        Turnuvaya kayıtlı takımları gösterir.
        """

        data = read_tournament_db()
        desc_lines = get_teams_desc(data)
        fixed_fields = {"author_name": "112'nin Corona Turnuvası Takım Listesi"}

        await self.send_and_control_pages(ctx, desc_lines, fixed_fields)

    @commands.command(name='teammate')
    async def get_potential_teammates(self, ctx):
        """
        Senin rankına uygun olabilecek takım arkadaşlarını gösterir.
        """

        user = check_registration(ctx.author.id)
        if user is not None:
            user_rank = user["statistics"]["pp_rank"]
        else:
            await ctx.send(
                f"Turnuvaya kayıtlı değilsin, kayıt olmak için `{settings['prefix']}register <osu username>` komutunu kullan.\n"
                f"Yardım için `{settings['prefix']}help` yazabilirsin.")
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

        desc_lines = get_player_desc(potential_teammates)
        fixed_fields = {"author_name": "Sana uygun takım arkadaşları listesi"}

        await self.send_and_control_pages(ctx, desc_lines, fixed_fields, )
        return


def setup(bot):
    bot.add_cog(Paged_Embed(bot))
