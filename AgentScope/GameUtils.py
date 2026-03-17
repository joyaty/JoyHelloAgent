
from typing import List, Dict
from collections import Counter

from agentscope.agent import ReActAgent

def  format_player_list(players: List[ReActAgent], show_role: bool = False):
    """格式化玩家列表"""
    if not players or len(players) <= 0:
        return "无人"
    
    if show_role:
        return "、".join([f"{p.name}({getattr(p, 'role', '未知')})" for p in players])
    else:
        return "、".join([p.name for p in players])
    

def majority_vote(votes: Dict[str, str]) -> tuple[str, int]:
    """投票统计"""
    if not votes:
        return ("无人", 0)
    
    vote_counts = Counter(votes.values())
    most_voted = vote_counts.most_common(1)[0]

    return most_voted[0], most_voted[1]
