
from agentscope.agent import ReActAgent
from agentscope.pipeline import MsgHub, sequential_pipeline, fanout_pipeline
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeMultiAgentFormatter

from GameRuleSetting import GameRoles, GetChineseName, MAX_GAME_ROUND, MAX_DISCUSSION_ROUND
from GameModerator import GameModerator
from GameUtils import format_player_list, majority_vote
from GameRolePrompt import GameRolePrompt
from OutputStructure import WitchActionModel, DiscussionModel, WerewolfKillModel, GetPeerActionModel, GetHunterActionModel, GetVoteActionModel, GetGuardActionModel

from dotenv import load_dotenv
import random
import os
import asyncio

class ThreeKingdomsWerewolfGame:
    """三国狼人杀游戏"""
    def __init__(self):
        self.name = "三国狼人杀游戏"
        self.moderator = GameModerator()
        self.players: dict[str, ReActAgent] = {}    ## 尝试所有的{玩家，Agent}映射关系表
        self.roles: dict[str, str] = {}             ## 场上所有的{玩家，角色}映射关系表
        self.alive_players: list[ReActAgent] = []   ## 场上存活的列表
        self.werewolves: list[ReActAgent] = []      ## 狼人角色列表
        self.seer: list[ReActAgent] = []            ## 预言家角色列表
        self.witch: list[ReActAgent] = []           ## 女巫角色列表
        self.hunter: list[ReActAgent] = []          ## 猎人角色列表
        self.guard: list[ReActAgent] = []           ## 守卫角色列表
        self.villagers: list[ReActAgent] = []       ## 普通村民列表
        # 标记女巫的道具状态
        self.witch_has_antidote = True
        self.witch_has_poison = True
        # 标记夜晚守卫的目标
        self.guard_target = None


    async def CreatePlayer(self, role: str, charactor: str) -> ReActAgent:
        """创建一名具有三国背景的玩家"""
        name = GetChineseName(charactor) 
        self.roles[name] = role
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


    async def SetupGame(self, player_count: int = 6):
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
            agent = await self.CreatePlayer(role, charactor)
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

        await self.moderator.Announce(f"三国狼人杀游戏开始！参与者：{format_player_list(self.alive_players)}")
        print(f"✅ 游戏设置完成，共{len(self.alive_players)}名玩家")

    async def GuardPhase(self):
        """夜晚守卫行动回合"""
        if not self.guard:
            return None
        ## 通知守卫开始行动
        guard_agent = self.guard[0]
        guard_result = await guard_agent(
            msg = await self.moderator.Announce("守卫请睁眼，选择今晚要守卫的目标..."),
            structured_model = GetGuardActionModel(self.alive_players)
        )
        if guard_result is None or not hasattr(guard_result, "metadata") or guard_result.metadata is None:
            print(f"⚠️ 守卫行动失败,视为空守")
            self.guard_target = None
        else:
            if guard_result.metadata.get("guard"):
                target_player = guard_result.metadata.get("target")
                self.guard_target = target_player

        guard_info = f"你守卫了{self.guard_target}" if self.guard_target else "你空守"
        guard_agent.observe(await self.moderator.Announce(guard_info))


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
         # 投票击杀
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
            # 检查vote_msg是否为None或metadata是否存在
            if vote_msg is not None and hasattr(vote_msg, 'metadata') and vote_msg.metadata is not None:
                votes[self.werewolves[i].name] = vote_msg.metadata.get('target')
            else:
                # 如果返回无效,随机选择一个目标
                print(f"⚠️ {self.werewolves[i].name} 的击杀投票无效,随机选择目标")
                valid_targets = [p.name for p in self.alive_players if p.name not in [w.name for w in self.werewolves]]
                votes[self.werewolves[i].name] = random.choice(valid_targets) if valid_targets else None

        killed_player, _ = majority_vote(votes)
        return killed_player


    async def SeerPhase(self):
        "预言家活动阶段"
        if not self.seer:
            return
        ## 主持人通知预言家可以开始查验存活的玩家
        seer_agent = self.seer[0]
        check_result = await seer_agent(
            msg = await self.moderator.Announce("🔮 预言家请睁眼，选择要查验的玩家..."),
            structured_model = GetPeerActionModel(self.alive_players)
        )
        ## 检测返回的结果是否有效
        if check_result is None or not hasattr(check_result, "metadata") or check_result.metadata is None:
            print(f"⚠️ 预言家查验失败,跳过此阶段")
            return
        
        target_name = check_result.metadata.get("target")
        if not target_name:
            print(f"⚠️ 预言家未选择查验目标,跳过此阶段")
            return
        ## 主持人检查当前玩家，并且告知预言家Agent结果
        target_role = self.roles.get(target_name, "村民")
        result_msg = f"查验结果:{target_name}是{'狼人'if target_role == '狼人' else '好人'}"
        await seer_agent.observe(await self.moderator.Announce(result_msg))


    async def WitchPhase(self, killed_player: str):
        """女巫夜晚行动回合"""
        if not self.witch:
            return
        ## 通知女巫
        witch_agent = self.witch[0] 
        await self.moderator.Announce("🧙‍♀️ 女巫请睁眼...")
        ## 告知女巫夜晚死亡信息
        dead_info = f"今晚{killed_player}被狼人击杀" if killed_player else "今晚平安无事"
        await witch_agent.observe(await self.moderator.Announce(dead_info))
        witch_action = await witch_agent(structured_model = WitchActionModel)
        saved_player = None
        poisoned_player = None

        # 检查返回结果是否有效
        if witch_action is None or not hasattr(witch_action, "metadata") or witch_action.metadata is None:
            print(f"⚠️ 女巫行动失败,视为不使用技能")
        else:
            if witch_action.metadata.get("use_antidote") and self.witch_has_antidote:
                if killed_player:
                    saved_player = killed_player
                    self.witch_has_antidote = False
                    await witch_agent.observe(await self.moderator.Announce(f"你使用解药救了{killed_player}"))

            if witch_action.metadata.get("use_poison") and self.witch_has_poison:
                poisoned_player = witch_action.metadata.get("target_name")
                if poisoned_player:
                    self.witch_has_poison = False
                    await witch_agent.observe(await self.moderator.Announce(f"你使用毒药毒杀了{poisoned_player}"))

        # 确定最终死亡玩家(非被救的狼人击杀玩家和女巫毒杀玩家)
        final_killed = killed_player if not saved_player else None
        return final_killed, poisoned_player 
    
    async def HunterPhase(self, shot_by_hunter: str):
        """猎人阶段"""
        if not self.hunter:
            return None
        
        hunter_agent = self.hunter[0]
        if hunter_agent.name == shot_by_hunter:
            
            hunter_action = await hunter_agent(
                msg = await self.moderator.Announce("🏹 猎人发动技能，可以带走一名玩家..."),
                structured_model = GetHunterActionModel(self.alive_players)
            )
            ## 检查返回结果是否有效
            if hunter_action is None and not hasattr(hunter_action, "metadata") or hunter_action.metadata is None:
                print(f"⚠️ 猎人技能使用失败,视为放弃开枪")
                return None
            
            if hunter_action.metadata.get("shoot"):
                target = hunter_action.metadata.get("target")
                if target:
                    # 获取猎人的开枪目标
                    await self.moderator.Announce(f"猎人{hunter_agent.name}开枪带走了{target}")
                    return target
                else:
                    print(f"⚠️ 猎人选择开枪但未指定目标,视为放弃")
                    return None
                
        return None
    

    def UpdateAlivePlayer(self, dead_players: list[str]):
        """更新存活玩家列表"""
        for dead_name in dead_players:
            if dead_name:
                # 从存活列表移除
                self.alive_players = [p for p in self.alive_players if p.name != dead_name]
                # 从各阵营移除
                self.werewolves = [p for p in self.alive_players if p.name != dead_name]
                self.villagers = [p for p in self.villagers if p.name != dead_name]
                self.seer = [p for p in self.seer if p.name != dead_name]
                self.witch = [p for p in self.witch if p.name != dead_name]
                self.hunter = [p for p in self.hunter if p.name != dead_name]
                self.guard = [p for p in self.guard if p.name != dead_name]


    async def DayPhase(self, round_num: int):
        """白天阶段"""
        await self.moderator.DayAnnouncement(round_num)

        async with MsgHub(
            self.alive_players,
            enable_auto_broadcast=True,
            announcement = await self.moderator.Announce(
                f"现在开始自由讨论。存活玩家：{format_player_list(self.alive_players)}"
            ),
        ) as all_hub:
            # 每人依序发言一轮
            await sequential_pipeline(self.alive_players)
            # 投票阶段，收集所有人的投票
            all_hub.set_auto_broadcast(False)
            vote_msgs = await fanout_pipeline(
                agents = self.alive_players,
                msg = await self.moderator.Announce("请投票选择要淘汰的玩家"),
                structured_model = GetVoteActionModel(self.alive_players)
            )
            # 统计票数
            vote_counts = {}
            for i, vote_msg in enumerate(vote_msgs):
                if vote_msg is not None and hasattr(vote_msg, "metadata") and vote_msg.metadata is not None:
                    vote_counts[self.alive_players[i].name] = vote_msg.metadata.get("vote")
                else:
                    print(f"⚠️ {self.alive_players[i].name} 的投票无效,视为弃票")
                    vote_counts[self.alive_players[i].name] = None

            out_player, vote_count = majority_vote(vote_counts)
            # 主持人公布投票结果
            await self.moderator.VoteResultAnnouncement(out_player, vote_count)
            return out_player
        
    def CheckOverCondition(self) -> str:
        """检查游戏结束条件"""
        alive_role = [self.roles.get(p.name, "村民") for p in self.alive_players]
        werewolf_count = alive_role.count("村民")
        villager_count = len(alive_role) - werewolf_count
        if werewolf_count == 0:
            return "好人阵营胜利！所有狼人已被淘汰"
        elif werewolf_count >= villager_count:
            return "狼人阵营胜利，狼人人数超过好人"
        
        return None

    async def RunGame(self):
        """运行游戏"""
        try:
            ## 初始化游戏设置
            await self.SetupGame(9)
            for round_num in range(1, MAX_GAME_ROUND + 1):
                print(f"\n🌙 === 第{round_num}轮游戏开始 ===")
                ## 夜晚阶段
                await self.moderator.NightAnnouncement(round_num)
                ## 夜晚狼人行动
                killed_player = await self.WerewolfPhase()
                ## 夜晚预言家行动
                await self.SeerPhase()
                ## 女巫夜晚行动
                final_killed, poison_killed = await self.WitchPhase(killed_player)
                ## 更新死亡玩家
                night_deaths = [p for p in [final_killed, poison_killed] if p]
                self.UpdateAlivePlayer(night_deaths)
                ## 死亡公告
                self.moderator.DeathAnnouncement(night_deaths)
                ## 检查胜利条件
                winner = self.CheckOverCondition()
                if winner:
                    await self.moderator.GameOverAnnouncement(winner)
                    return
                ## 白天阶段
                vote_out = await self.DayPhase(round_num)
                hunter_killed = await self.HunterPhase(vote_out)
                ## 更新死亡玩家
                night_deaths = [p for p in [final_killed, poison_killed] if p]
                self.UpdateAlivePlayer(night_deaths)
                ## 死亡公告
                self.moderator.DeathAnnouncement(night_deaths)
                ## 检查胜利条件
                winner = self.CheckOverCondition()
                if winner:
                    await self.moderator.GameOverAnnouncement(winner)
                    return
                ## 总结本轮，准备下一轮
                print(f"第{round_num}轮结束，存活玩家：{format_player_list(self.alive_players)}")
        except Exception as e:
            print(f"❌ 游戏运行出错：{e}")
            import traceback
            traceback.print_exc()

async def main():
    """主函数"""
    load_dotenv()
    if "ALI_API_KEY" not in os.environ:
        print("❌ 请设置环境变量 ALI_API_KEY")
        return
    print("🎮 欢迎来到三国狼人杀！")
    # 创建并运行游戏
    game = ThreeKingdomsWerewolfGame()
    await game.RunGame()
    
if __name__ == "__main__":
    asyncio.run(main())
