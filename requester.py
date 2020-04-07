import os
import json
import requests
from bs4 import BeautifulSoup
from oppai import ezpp_set_autocalc, ezpp_new, ezpp_data_dup


def get_user_info(username):
    r = requests.get(f"https://osu.ppy.sh/users/{username}")
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        json_user = soup.find(id="json-user").string
    except:
        raise Exception(f"`{username}` adlı kişiyi osu!'da bulamadım.")
    user_dict = json.loads(json_user)

    return user_dict


def get_map_info(map_id):
    r = requests.get(f"https://osu.ppy.sh/b/{map_id}")
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        json_bmap = soup.find(id="json-beatmapset").string
    except:
        raise Exception(f"`{map_id}` id'li mapi osu!'da bulamadım.")
    bmap_dict = json.loads(json_bmap)

    try:
        osu_file = requests.get(f"https://bloodcat.com/osu/b/{map_id}")
    except:
        raise Exception(f"`{map_id}` bloodcat'te bulunamadı.")

    osu_file_contents = osu_file.content

    ezpp_map = ezpp_new()
    ezpp_set_autocalc(ezpp_map, 1)
    ezpp_data_dup(ezpp_map, osu_file_contents.decode('utf-8'), len(osu_file_contents))

    return bmap_dict, ezpp_map

def get_match_info(match_link):
    key = os.environ["OSU_MP_LINK"] 

    match_id = match_link.split("/")[-1]
    r = requests.get(f"https://osu.ppy.sh/api/get_match?k={key}&mp={match_id}")
    match_data = json.loads(r.text)

    matches_without_abort = []
    for index, game in enumerate(match_data["games"]):
        if index == len(match_data["games"]) or match_data["games"][index+1]["beatmap_id"] != game["beatmap_id"]:
            matches_without_abort.append(game)

    return matches_without_abort
