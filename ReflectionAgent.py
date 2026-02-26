"""
基于Reflection范式的Agent实现
"""

from Memory import Memory
from OpenAICompatibleClient import OpenAICompatibleClient

## 首次任务提示词模板
INITIAL_PROMPT_TEMPLATE = """
你是一位资深的Python程序员。请根据以下要求，编写一个Python函数。
你的代码必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范。

要求: {task}

请直接输出代码，不要包含任何额外的解释。
"""

## 代码审查与反馈提示词模板
CODEREVIEW_PROMPT_TEMPLATE = """
你是一位极其严格的代码评审专家和资深算法工程师，对代码的性能有极致的要求。
你的任务是审查以下Python代码，并专注于找出其在<strong>算法效率</strong>上的主要瓶颈。

# 原始任务:
{task}

# 待审查的代码:
```python
{code}
```

请分析该代码的时间复杂度，并思考是否存在一种<strong>算法上更优</strong>的解决方案来显著提升性能。
如果存在，请清晰地指出当前算法的不足，并提出具体的、可行的改进算法建议（例如，使用筛法替代试除法）。
如果代码在算法层面已经达到最优，才能回答“无需改进”。

请直接输出你的反馈，不要包含任何额外的解释。
"""

## 代码重构提示词模板
REFACTOR_PROMPT_TEMPLATE = """
你是一位资深的Python程序员。你正在根据一位代码评审专家的反馈来优化你的代码。

# 原始任务:
{task}

# 你上一轮尝试的代码:
{last_code_attempt}
评审员的反馈：
{feedback}

请根据评审员的反馈，生成一个优化后的新版本代码。
你的代码必须包含完整的函数签名、文档字符串，并遵循PEP 8编码规范。
请直接输出优化后的代码，不要包含任何额外的解释。
"""

class ReflectionAgent:
    """
    基于Reflection范式的智能体实现。该智能体通过不断地生成代码、接受评审反馈并重构代码来逐步优化解决方案。
    """
    def __init__(self, llm_client : OpenAICompatibleClient, max_iterations: int = 3):
        self.llm_client = llm_client            ## LLM客户端
        self.max_iteration = max_iterations     ## 最大迭代次数
        self.memory = Memory()


    def run(self, task: str) -> str:
        print(f"\n -------- 开始处理任务 -------- \n任务内容:{task}\n")
        ## 1. 构成代码生成提示词，调用LLM生成初始代码
        codeGen_prompt = INITIAL_PROMPT_TEMPLATE.format(task=task)
        response = self.llm_client.think(codeGen_prompt, system_prompt="")
        self.memory.add_record("execution", response)
        ## 2. 进入反思循环，进行代码审查和重构
        for iteration in range(self.max_iteration):
            print(f"---- 迭代 {iteration+1}/{self.max_iteration} ----\n")
            last_code = self.memory.get_last_execution()
            if not last_code:
                print("没有找到上一轮的代码记录，结束迭代。")
                break
            ## 构造代码审查提示词，提交给LLM获取修改建议
            codereview_prompt = CODEREVIEW_PROMPT_TEMPLATE.format(task=task, code=last_code)
            review_response = self.llm_client.think(codereview_prompt, system_prompt="")
            if "无需改进" in review_response:
                print("评审员认为代码无需改进，结束代码审查迭代")
                break
            ## 记录评审反馈
            print(f"评审员反馈:\n{review_response}\n")
            self.memory.add_record("reflection", review_response)
            ## 构造重构提示词，提交给LLM获取优化后的代码
            refactor_prompt = REFACTOR_PROMPT_TEMPLATE.format(task=task, last_code_attempt=last_code, feedback=review_response)
            refactor_code = self.llm_client.think(refactor_prompt, system_prompt="")
            ## 记录重构后的代码
            self.memory.add_record("execution", refactor_code)

        ## 3. 最终返回最后一次的代码尝试
        final_code = self.memory.get_last_execution()
        print(f"最终生成的代码:\n{final_code}\n")
        return final_code


if __name__ == "__main__":
    """
    ReflectionAgent的测试用例，任务是编写一个函数，找出1到n之间所有的素数。
    """
    llm_client = OpenAICompatibleClient()
    agent = ReflectionAgent(llm_client)
    task = "编写一个Python函数，找出1到n之间所有的素数 (prime numbers)。"
    final_code = agent.run(task)