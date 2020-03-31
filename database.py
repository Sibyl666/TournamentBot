import os
import json
import requests
import math
import discord
import asyncio
from copy import deepcopy
from discord.ext import commands
from bs4 import BeautifulSoup


mappool_db_file = "beatmaps.json"
old_maps_filename = "old_maps.tsv"
tournament_db_file = "turnuva.json"
settings_file = "settings.json"

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

