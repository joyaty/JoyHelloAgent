
from OpenAICompatibleClient import OpenAICompatibleClient
import ast

## 规划器的提示词
PLANER_TOOL_PROMPT = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划,```python与```作为前后缀是必要的:
```python
["步骤1", "步骤2", "步骤3", ...]   
```
"""

class Planer:
    """
    AI任务规划器，将初始问题，划分为若干个子任务列表
    """
    def __init__(self, llm_client: OpenAICompatibleClient):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        prompt = PLANER_TOOL_PROMPT.format(question=question)
        response = self.llm_client.think(prompt=prompt, system_prompt="")
        try:
            response_content =response.split("```python")[1].split("```")[0].strip() # 裁剪掉代码块的标识符，获取代码块内容
            result = ast.literal_eval(response_content)  ## ast.literal_eval可以安全的将字符串解析为python对象，这里按照约定，应该是个python列表
            return result if isinstance(result, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"解析规划器输出时发生错误: {e}")
            print(f"原始内容: {response}")
            return []
        except Exception as e:
            print(f"解析规划器输出时发生未知错误: {e}")
            return []

### 执行器提示词
SOLVER_TOOL_PROMPT = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。 
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决“当前步骤”，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对“当前步骤”的回答:
"""

class Solver:
    """
    AI任务执行器，严格按照规划器生成的子任务列表，逐个执行子任务
    """
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def solve(self, question: str, tasks: list[str]):
        history = "" ## 用于存储历史步骤和结果
        response = "" ## 用于存储当前步骤的结果(python无块作用域，其实只要保证循环至少执行一次，可以不用声明而执行在循环内赋值，循环外也可使用，这里为了代码清晰和健壮(避免循环没有执行)而提取声明下)
        for i, step in enumerate(tasks):
            print(f"正在执行步骤 {i+1}/{len(tasks)}: {step}")
            prompt = SOLVER_TOOL_PROMPT.format(question=question, plan=tasks, history=history, current_step=step)
            response = self.llm_client.think(prompt = prompt, system_prompt = "")
            history += f"步骤{i+1}: {step}\n结果:{response}\n\n" ## 将当前步骤和结果添加到历史中，供后续步骤可以参考历史信息进行回答
            print(f"步骤{i+1}的执行结果: {response}\n")

        final_answer = response
        return final_answer


class PlanAndSolveAgent:
    """
    基于Plan-Solve范式的智能体
    """
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.planer = Planer(llm_client)
        self.solver = Solver(llm_client)

    def run(self, question: str):
        print(f"开始处理问题: {question}\n")
        print("=== 规划阶段 ===")
        plan = self.planer.plan(question)
        print(f"生成执行的规划: {plan}\n")

        if not plan or len(plan) == 0:
            print("规划的任务列表为空，无法继续执行。请检查规划其的输出")
            return
        
        print("=== 执行阶段 ===")
        final_answer = self.solver.solve(question, plan)
        print(f"最终答案: {final_answer}\n")

if __name__ == "__main__":
    llm_client = OpenAICompatibleClient()
    agent = PlanAndSolveAgent(llm_client)
    question = "一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？"
    agent.run(question)