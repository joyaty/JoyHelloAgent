""""
Memory模块，负责记录智能体的历史对话和行动记录，提供接口供规划器和求解器查询历史信息。
"""
from typing import List, Dict, Any, Optional

class Memory:
    """
    简易的记忆模块，用于记录智能体的历史对话和行动记录。
    """
    def __init__(self):
        """
        初始化记忆模块，创建一个空的记录列表
        """
        self.records: List[Dict[str, Any]] = [] ## 用于存储历史对话记录

    def add_record(self, record_type: str, content: str):
        """
        向记忆中添加一条记录
        参数:
        - record_type: 记录的类型("execution"或者"reflection")
        - content: 记录的具体内容(生成的代码或者反思的反馈)
        """
        record = { 
            "type": record_type, # 
            "content": content # 
        }
        self.records.append(record)

    def get_trajectory(self) -> str:
        """
        获取当前的记忆数据，按照一定的格式组织成字符串返回
        """
        trajectory_parts = []
        for record in self.records:
            if record["type"] == "execution":
                trajectory_parts.append(f"--- 上一轮尝试(代码) ---\n{record['content']}")
            elif record["type"] == "reflection":
                trajectory_parts.append(f"--- 评审员反馈 ---\n{record['content']}")

        return "\n\n".join(trajectory_parts)
    
    def get_last_execution(self) -> Optional[str]:
        """
        获取最后一次的execution类型记录内容(这是最终结果)
        """
        for record in reversed(self.records):
            if record["type"] == "execution":
                return record["content"]
        return None
 