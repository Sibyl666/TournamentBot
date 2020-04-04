from discord.ext import commands

from database import read_tournament_db, write_tournament_db, get_settings
from rank_calculations import get_user_weight, get_teammate_rank
from registration_check import check_registration

settings = get_settings()


class Teams(commands.Cog):

    @commands.command(name='team')
    async def create_team(self, ctx, osu_user2, team_name):
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
            await ctx.send(
                f"Takım oluşturmadan önce turnuvaya kayıt olmalısın.\nKullanım: `{settings['prefix']}register`")
            return

        print(f"?team {osu_user2} {team_name}")
        if osu_user2.startswith("<@!"):
            user2_discord_id = osu_user2[3:-1]
        elif osu_user2.startswith("<@"):
            user2_discord_id = osu_user2[2:-1]
        else:
            await ctx.send(f"Kullanım: `{settings['prefix']}team @oyuncu takım_ismi`\n"
                           f"Ex: `{settings['prefix']}team @heyronii asdasfazamaz`")
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

        if user1_weight + user2_weight > settings["rank_limit"]:
            await ctx.send(
                f"Takımın toplam değeri sınırın üzerinde kaldığı için katılamazsınız."
                f"\nTakımınızın toplam değeri: {user1_weight + user2_weight:.0f} > {settings['rank_limit']}")
        else:
            new_team = {"name": team_name, "user1": ctx.author.id, "user2": user2_discord_id}
            db["teams"].append(new_team)
            await ctx.send(f"`{team_name}` başarıyla turnuvaya katıldı!")

        write_tournament_db(db)
        return

    @commands.command(name='rankcheck')
    async def check_player_rank(self, ctx, rank=None):
        """
        Katılabileceğiniz takım arkadaşınızın maximum rankını gösterir
        rank: Optional - Rank aralığını öğrenmek istediğiniz kişinin rankı
        """

        if rank is not None:
            try:
                p1_rank = int(rank)
                teammate_min_rank = get_teammate_rank(p1_rank)
            except:
                await ctx.send(f"Usage: {settings['prefix']}rankcheck <optional: rank>")
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


def setup(bot):
    bot.add_cog(Teams(bot))
