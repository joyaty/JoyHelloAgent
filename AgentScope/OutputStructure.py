
from pydantic import BaseModel, Field
from typing import Optional, Literal
from agentscope.agent import AgentBase

class DiscussionModel(BaseModel):
    """讨论阶段的回答格式"""
    reach_agreement: bool = Field(
        description = "是否已达成一致意见"
    )
    confidence_level: int = Field(
        description = "对当前推理的信心程度(1-10)",
        ge = 1,
        le = 10
    )
    key_evidence: Optional[str] = Field(
        description = "支持你观点的关键证据",
        default = None
    )


class WerewolfKillModel(BaseModel):
    """狼人击杀阶段的回答格式"""
    target: str = Field(
        description = "要击杀的玩家"
    )
    kill_stratege: str = Field(
        description = "击杀策略说明"
    )
    team_coordination: str = Field(
        description = "与狼队友的配合计划",
        default = None
    )


def GetPeerActionModel(alive_agents: list[AgentBase]) -> type[BaseModel]:
    """预言家夜晚行动回合的回答格式"""
    class PeerActionModel(BaseModel):
        target: Literal[tuple(_.name for _ in alive_agents)] = Field(
            description = "要查验的玩家"
        )
        check_reason: str = Field(
            description = "查验此人的原因"
        )
        priority_level: int = Field(
            description = "查验优先级(1-10)",
            ge = 1,
            le = 10
        )

    return PeerActionModel


class WitchActionModel(BaseModel):
    """女巫夜晚行动回合的回答格式"""
    use_antidote: bool = Field(
        description = "是否使用解药救人",
        default = False
    )
    use_poison: bool = Field(
        description = "是否使用毒药杀人",
        default = False
    )
    target_name: Optional[str] = Field(
        description = "毒杀的目标玩家",
        default = None
    )
    action_reason: Optional[str] = Field(
        description = "行动理由",
        default = None
    )


def GetHunterActionModel(alive_agents: list[AgentBase]) -> type[BaseModel]:
    """猎人死亡后的行动回答格式"""
    class HunterActionModel(BaseModel):

        shoot: bool = Field(
            description = "是否使用开枪技能"
        )

        target: Optional[Literal[tuple(_.name for _ in alive_agents)]] = Field(
            description = "开球目标玩家姓名",
            default = None
        )

        shoot_reason: Optional[str] = Field(
            description = "开枪理由",
            default = None
        ) 

    return HunterActionModel

def GetGuardActionModel(alive_agents: list[AgentBase]) -> type[BaseModel]:
    """猎人死亡后的行动回答格式"""
    class GuardActionModel(BaseModel):

        guard: bool = Field(
            description = "是否使用守卫技能"
        )

        target: Optional[Literal[tuple(_.name for _ in alive_agents)]] = Field(
            description = "守卫的目标玩家姓名",
            default = None
        )

        guard_reason: Optional[str] = Field(
            description = "守卫理由",
            default = None
        ) 

    return GuardActionModel


def GetVoteActionModel(alive_agents: list[AgentBase]) -> type[BaseModel]:
    """投票回合的回答格式"""
    class VoteActionModel(BaseModel):
        vote: Literal[tuple(_.name for _ in alive_agents)] = Field(
            description = "你要投票淘汰的玩家姓名"
        )
        reason: str = Field(
            description = "投票理由，简要说明为什么选择此人"
        )
        suspicion_level: int = Field(
            description = "对被投票者的怀疑程度(1-10)",
            ge = 1,
            le = 10
        )

    return VoteActionModel
