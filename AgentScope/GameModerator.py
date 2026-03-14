
from agentscope.agent import AgentBase
from agentscope.message import Msg
from typing import List

class GameModerator(AgentBase):
    """定义游戏主持人类"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "游戏主持人"
        self.game_log: List[str] = []

    async def Announce(self, content: str) -> Msg:
        """发布游戏公告"""
        msg = Msg(
            name = self.name,
            content = content,
            role = "system"
        )
        self.game_log.append(content)
        await self.print(msg)
        return msg
    
    async def NightAnnouncement(self, round_num: int) -> Msg:
        """夜晚阶段公告"""
        content = f"🌙 第{round_num}夜降临，天黑请闭眼..."
        return await self.Announce(content)
    
    async def DayAnnouncement(self, round_num: int) -> Msg:
        """白天阶段公告"""
        content = f"☀️ 第{round_num}天天亮了，请大家睁眼..."
        return await self.Announce(content)
    
    async def DeathAnnouncement(self, dead_players: List[str]) -> Msg:
        """夜晚死亡消息公告"""
        if not dead_players or dead_players.count() <= 0:
            content = "昨天晚上是平安夜"
        else:
            content = f"昨晚，玩家{GameModerator.format_player_list(dead_players)}死亡"
        return await self.Announce(content)
    
    async def VoteResultAnnouncement(self, voted_out: str, vote_count: int) -> Msg:
        """白天投票结果公告"""
        content = f"投票结果：{voted_out}以{vote_count}票被淘汰出局。"
        return await self.Announce(content)
    
    async def GameOverAnnouncement(self, winner: str) -> Msg:
        """游戏结束公告"""
        content = f"🎉 游戏结束！{winner}胜利"
        return await self.Announce(content)
        