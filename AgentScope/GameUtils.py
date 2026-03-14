
from typing import List, Dict
from collections import Counter

def format_player_list(players: List[str]):
    """格式化玩家列表"""
    if players == None or players.count() <= 0:
        return "无人"
    else:
        return "、".join(players)
    

def majority_vote(votes: Dict[str, str]) -> tuple[str, int]:
    """投票统计"""
    if not votes:
        return ("无人", 0)
    
    vote_counts = Counter(votes.values())
    most_voted = vote_counts.most_common(1)[0]

    return most_voted[0], most_voted[1]