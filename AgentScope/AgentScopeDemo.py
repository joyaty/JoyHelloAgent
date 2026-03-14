
from agentscope.agent import ReActAgent
from agentscope.pipeline import MsgHub, sequential_pipeline, fanout_pipeline
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeMultiAgentFormatter

from GameRuleSetting import GameRoles, GetChineseName, MAX_GAME_ROUND, MAX_DISCUSSION_ROUND
from GameModerator import GameModerator
from GameUtils import format_player_list, majority_vote
from GameRolePrompt import GameRolePrompt
from OutputStructure import WitchActionModel, DiscussionModel, WerewolfKillModel

from typing import Dict, List
import random
import os

class ThreeKingdomsWerewolfGame:
    """三国狼人杀游戏"""
    def __init___(self):
        self.name = "三国狼人杀游戏"
        self.moderator = GameModerator()
        self.players: Dict[str, ReActAgent] = {}
        self.roles: Dict[str, str] = {}
        self.alive_players: List[ReActAgent] = []   ## 场上存活的列表
        self.werewolves: List[ReActAgent] = []      ## 狼人角色列表
        self.seer: List[ReActAgent] = []            ## 预言家角色列表
        self.witch: List[ReActAgent] = []           ## 女巫角色列表
        self.hunter: List[ReActAgent] = []          ## 猎人角色列表
        self.guard: List[ReActAgent] = []           ## 守卫角色列表
        self.villagers: List[ReActAgent] = []       ## 普通村民列表


    async def CreatePlayer(self, role: str, charactor: str) -> ReActAgent:
        """创建一名具有三国背景的玩家"""
        name = GetChineseName(charactor) 
        self.roles[role] = name
        agent = ReActAgent(
            name = name,
            sys_prompt = GameRolePrompt.GetRolePrompt(role, charactor),
            model = DashScopeChatModel( 
                model_name = "qwen-max",
                api_key = os.getenv("ALI_API_KEY"),
                enable_thinking = True
            ),
            
            formatter = DashScopeMultiAgentFormatter()
        )
        ## 确认身份
        await agent.observe(
            await self.moderator.Announce(
                f"[{name}]你在这场三国狼人杀中扮演{role},你的角色是{charactor}。{GameRoles.GetRoleAbility(role)}"
            )
        )
        self.players[name] = agent
        return agent


    def SetupGame(self, player_count: int = 6):
        """初始化游戏"""
        print("🎮 开始设置三国狼人杀游戏...")
        ## 获取游戏配置
        roles = GameRoles.GetStandardSetup(player_count)
        charactors = random.sample([
            "刘备", "关羽", "张飞", "诸葛亮", "赵云",
            "曹操", "司马懿", "周瑜", "孙权"
        ], player_count)
        ## 创建玩家
        for role, charactor in zip(roles, charactors):
            agent = self.CreatePlayer(role, charactor)
            self.alive_players.append(agent)
            # 分配到对应阵营
            if role == "狼人":
                self.werewolves.append(agent)
            elif role == "预言家":
                self.seer.append(agent)
            elif role == "女巫":
                self.witch.append(agent)
            elif role == "猎人":
                self.hunter.append(agent)
            elif role == "守卫":
                self.guard.append(agent)
            else:
                self.villagers.append(agent)

        self.moderator.Announce(f"三国狼人杀游戏开始！参与者：{format_player_list(self.alive_players)}")


    async def WerewolfPhase(self):
        """夜晚狼人活动阶段"""
        if not self.werewolves:
            return None
        
        await self.moderator.Announce("狼人请睁眼，选择今晚要击杀的目标...")

        async with MsgHub(
            self.werewolves,
            enable_auto_broadcast = True,
            announcement = await self.moderator.Announce(
                f"狼人们，请讨论今晚的击杀目标。存活玩家: {format_player_list(self.alive_players)}"
            )
        ) as werewolves_hub:
            # 讨论阶段
            for _ in range(MAX_DISCUSSION_ROUND):
                for wolf in self.werewolves:
                    await wolf(structured_model=DiscussionModel)

        werewolves_hub.set_auto_broadcast(False)
        kill_votes = await fanout_pipeline(
            self.werewolves,
            msg = await self.moderator.Announce("请选择击杀目标"),
            structured_model = WerewolfKillModel,
            enable_gather = False,
        )
        ## 统计投票
        votes = {}
        for i, vote_msg in enumerate(kill_votes):
            if vote_msg is not None and hasattr(vote_msg, 'metadata') and vote_msg.metadata is not None:
                votes[self.werewolves[i].name] = vote_msg.metadata.get('target')
            else:
                print(f"⚠️ {self.werewolves[i].name} 的击杀投票无效,随机选择目标")
                valid_targets = [p.name for p in self.alive_players if p.name not in [w.name for w in self.werewolves]]
                votes[self.werewolves[i].name] = random.choice(valid_targets) if valid_targets else None

        killed_player, _ = majority_vote(votes)

    def RunGame(self):
        """运行游戏"""

        for round in range(MAX_GAME_ROUND):
            print(f"第{round}回合开始")



if __name__ == "__main__":
    pass ## TODO
