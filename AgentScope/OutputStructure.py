
from pydantic import BaseModel, Field
from typing import Optional

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
    action_reson = Optional[str] = Field(
        description = "行动理由",
        default = False
    )

