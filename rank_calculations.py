import math

from database import read_tournament_db, write_tournament_db , get_settings
from requester import get_user_info

settings = get_settings()

def get_user_weight(rank):
    # Ugly function to calculate user's rank weight
    return (19273 - 1371 * math.log(rank + 1000)) - (1000 * (1371 / (rank + 1000)))



def get_teammate_rank(rank):
    user1_weight = get_user_weight(rank)
    user2_weight = settings["rank_limit"] - user1_weight
    return binary_search(user2_weight)



def binary_search(weight):
    rank_upper = 100000000
    rank_lower = 1
    while not rank_upper == rank_lower:
        rank_mid = (rank_upper + rank_lower) // 2
        temp_weight = get_user_weight(rank_mid)
        if weight > temp_weight:
            rank_upper = rank_mid
        else:
            rank_lower = rank_mid + 1

    return rank_mid
