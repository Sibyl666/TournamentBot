import os
import json

mappool_db_file = "beatmaps.json"
old_maps_filename = "old_maps.tsv"
tournament_db_file = "turnuva.json"
lobby_db_file = "lobbies.json"
settings_file = "settings.json"
qualifier_results_file = "qualifier_results.json"

def read_qualifier_results_db():
    if not os.path.exists(qualifier_results_file):

        mappool_db = read_mappool_db()
        empty_db = {"maps":{}, "final_result":{"message_id":None, "page":1, "final_scores": []}}
        for map_id, map_data in mappool_db.items():
            
            map_info = {}
            map_info["qualifier_scores"] = []
            map_info["qualifier_message_id"] = None
            map_info["page"] = 1
            map_info["modpool"] = map_data["modpool"]
            map_info["artist"] = map_data["artist"]
            map_info["title"] = map_data["title"]
            for diff in map_data["beatmaps"]:
                if str(diff["id"]) == map_id:
                    map_info["diff_name"] = diff["version"]
            
            empty_db["maps"][map_id] = map_info

        with open(qualifier_results_file, "w", encoding='utf-8') as f:
            json.dump(empty_db, f)
        return empty_db

    with open(qualifier_results_file, "r", encoding='utf-8') as f:
        db = json.load(f)

    return db

def write_qualifier_results_db(db):
    with open(qualifier_results_file, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=2)

    return


def read_lobby_db():
    if not os.path.exists(lobby_db_file):
        with open(lobby_db_file, "w", encoding='utf-8') as f:
            json.dump({}, f)
        return {}

    with open(lobby_db_file, "r", encoding='utf-8') as f:
        db = json.load(f)

    return db


def write_lobby_db(db):
    with open(lobby_db_file, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=2)

    return


def read_mappool_db():
    if not os.path.exists(mappool_db_file):
        with open(mappool_db_file, "w", encoding='utf-8') as f:
            json.dump({}, f)
        return {}

    with open(mappool_db_file, "r", encoding='utf-8') as f:
        db = json.load(f)

    return db


def write_mappool_db(db):
    with open(mappool_db_file, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=2)

    return


def get_old_maps():
    with open(old_maps_filename, "r") as f:
        old_maps = f.read().splitlines()

    old_map_ids = [bmap.split("\t")[7] for bmap in old_maps]

    return old_map_ids


def read_tournament_db():
    if not os.path.exists(tournament_db_file):
        with open(tournament_db_file, "w", encoding='utf-8') as f:
            json.dump({"teams": [], "users": []}, f)

        return {"teams": [], "users": []}

    with open(tournament_db_file, "r", encoding='utf-8') as f:
        db = json.load(f)

    db["users"].sort(key=lambda e: e['statistics']['pp_rank'])

    return db


def write_tournament_db(db):
    with open(tournament_db_file, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=2)

    players_by_discord = {}
    db["users"].sort(key=lambda e: e['statistics']['pp_rank'])

    for player in db["users"]:
        discord_id = str(player["discord_id"])
        players_by_discord[discord_id] = player

    return


def get_settings():
    with open(settings_file, "r", encoding='utf-8') as f:
        data = json.load(f)

    return data
