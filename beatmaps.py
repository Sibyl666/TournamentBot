import discord
from oppai import ezpp_mods, ezpp_set_mods, ezpp_stars, MODS_HR, MODS_DT
from discord.ext import commands

from database import read_mappool_db, write_mappool_db, get_old_maps, get_settings
from requester import get_map_info

settings = get_settings()


class Mappool(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="poolannounce")
    @commands.has_permissions(administrator=True)
    async def announce_mappool(self, ctx, which_pool):
        channel = self.bot.get_channel(693814385260494918)
        mappool_db = read_mappool_db()

        mods = ["NM", "HD", "HR", "DT", "FM", "TB"]
        which_pool = which_pool.upper()
        if which_pool == "QF":
            mods = mods[:4]
        for mod in mods:
            bmaps = [(bmap_id, bmap) for bmap_id, bmap in mappool_db.items() if
                     bmap["mappool"] == which_pool and bmap["modpool"] == mod]

            await self.show_single_mod_pool(channel, bmaps, which_pool, mod)

    @commands.command(name='poolshow')
    @commands.has_role("Mappool")
    async def mappool_show(self, ctx, which_pool, mod=None):
        """
        Shows the selected pool
        which_pool: Must be one of [QF, W1, W2]
        mod: (Optional) Can be one of [NM, HD, HR, DT, FM, TB], if not given, bot will display all the maps in the pool
        """
        mappool_db = read_mappool_db()

        mods = ["NM", "HD", "HR", "DT", "FM", "TB"]
        which_pool = which_pool.upper()
        show_all = False
        if mod is None:
            show_all = True
        else:
            mod = mod.upper()

        if show_all:
            if which_pool == "QF":
                mods = mods[:4]
            for mod in mods:
                bmaps = [(bmap_id, bmap) for bmap_id, bmap in mappool_db.items() if
                         bmap["mappool"] == which_pool and bmap["modpool"] == mod]

                await self.show_single_mod_pool(ctx, bmaps, which_pool, mod)
        else:
            bmaps = [(bmap_id, bmap) for bmap_id, bmap in mappool_db.items() if
                     bmap["mappool"] == which_pool and bmap["modpool"] == mod]
            await self.show_single_mod_pool(ctx, bmaps, which_pool, mod)

        return

    async def show_single_mod_pool(self, ctx, bmaps, which_pool, mod):

        color = discord.Color.from_rgb(*settings["mod_colors"][mod])
        desc_text = ""
        for bmap_id, bmapset in bmaps:
            bmap = next(item for item in bmapset["beatmaps"] if item["id"] == int(bmap_id))
            bpm = bmap["bpm"]
            length = bmap["hit_length"]
            star_rating = bmap["difficulty_rating"]
            if mod == "DT":
                length = int(length // 1.5)
                bpm = bpm * 1.5

            bmap_url = bmap['url']
            bmap_name = f"{bmapset['artist']} - {bmapset['title']} [{bmap['version']}]"
            desc_text += f"▸[{bmap_name}]({bmap_url})\n" \
                         f"▸Length: {length // 60}:{length % 60:02d} ▸Bpm: {bpm:.1f} ▸SR: {star_rating}* \n\n"

        author_name = f"112'nin Corona Turnuvası Beatmaps in {which_pool} - {mod}"
        embed = discord.Embed(description=desc_text, color=color)
        embed.set_thumbnail(
            url=settings["mod_icons"][mod])
        embed.set_author(name=author_name)
        await ctx.send(embed=embed)

        return

    @commands.command(name='mappool')
    @commands.has_role("Mappool")
    async def mappool(self, ctx, action, map_link=None, which_pool=None, mod=None, comment=""):
        """
        Add, remove or show maps from the mappools

        action: "add", "remove"
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

            pools = ["QF", "W1", "W2","W3"]
            if which_pool not in pools:
                await ctx.send(f"Mappools can only be QF, W1, W2 or W3.\n"
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
                               f"Requested command: {settings['prefix']}{ctx.command.name} {ctx.args[1:]}")
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
            elif which_pool == "W1":
                max_maps = [4, 2, 2, 3, 2, 1]
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

            embed = discord.Embed(title=title_text, description=desc_text,
                                  color=discord.Color.from_rgb(*settings["tournament_color"]), url=bmap_url)
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
            except KeyError:
                await ctx.send(f"The specified beatmap does not exist in the pools.\n"
                               f"You wanted to remove <{map_link}>.")
                return

            write_mappool_db(mappool_db)
            await ctx.send(f"Successfully deleted <{map_link}> from pools.")

            return


def setup(bot):
    bot.add_cog(Mappool(bot))
