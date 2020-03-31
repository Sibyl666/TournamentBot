
from database import read_tournament_db

def get_players_by_discord():
    db = read_tournament_db()
    players_by_discord = {}

    for player in db["users"]:
        discord_id = str(player["discord_id"])
        players_by_discord[discord_id] = player

    return players_by_discord

def check_registration(user_discord):
    user_discord = str(user_discord)

    players_by_discord = get_players_by_discord()

    if user_discord in players_by_discord:
        user = players_by_discord[user_discord]
        return user
    else:
        return None

