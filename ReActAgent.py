"""
智能体范式ReAct (Reason + Act)
模仿人类解决问题的方式，将推理 (Reasoning) 与行动 (Acting) 显式地结合起来，形成一个“思考-行动-观察”的循环
"""

from OpenAICompatibleClient import OpenAICompatibleClient
from Tools import ToolExecutor
from Tools import search
import re

# ReAct 提示词模板
REACT_SYSTEM_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下:
{tools}

请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`:调用一个可用工具。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 Finish[最终答案] 来输出最终答案。

"""

REACT_USER_PROMPT_TEMPLATE = """
现在，请开始解决以下问题:
Question: {question}
History: {history}
"""

class ReActAgent:
    """
    基于ReAct(Reason + Act)范式的智能体
    """
    def __init__(self, llm_client: OpenAICompatibleClient, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client            ## LLM客户端
        self.tool_executor = tool_executor      ## 工具箱
        self.max_steps = max_steps              ## 最大的循环次数
        self.history = []                       ## 历史记录


    def run(self, question: str):
        """
        ReAct范式智能体循环
        """
        self.history = []
        current_step = 0
        ## 格式化系统提示词
        system_prompt = REACT_SYSTEM_PROMPT_TEMPLATE.format(tools = self.tool_executor.getAvailableToolsDesc())
        is_success = False
        while not is_success and current_step < self.max_steps:
            current_step += 1
            print(f"------第{current_step}步--------")
            ## 历史记录转字符串
            history_str = "\n".join(self.history)
            ## 格式化当前上下文提示词
            user_prompt = REACT_USER_PROMPT_TEMPLATE.format(question = question, history = history_str)
            ## 调用LLM进行思考
            response = self.llm_client.think(user_prompt, system_prompt)
            if not response:
                print("LLM思考失败")
                break
            ## 解析大模型思考结果，觉得下一步是调用工具，还是可以结束输出结果
            thought, action = self._parse_output(response)
            if thought:
                print(thought)
            if action:
                print(action)

            if action.startswith("Finish"):
                # Finish指令，表示LLM获取了最终结果，可以打印并结束
                final_answer = re.match(r"Finish\[(.*)\]", action, re.DOTALL).group(1)
                print(f"最终答案：{final_answer}")
                is_success = True
                break

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                # 异常的工具调用Action格式
                continue

            print(f"Action: {tool_name}[{tool_input}]")
            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"错误: 未找到名为'{tool_name}'的工具"
            else:
                observation = tool_function(tool_input) ## 调用工具获取结果

            print(f"Observation: {observation}")
            ## 将本轮的Action和Observation添加到历史记录中
            self.history.append(f"Action:{action}")
            self.history.append(f"Observation:{observation}")

        if not is_success:
            print("出现异常或者抵达最大步数，流程终止")


    def _parse_output(self, text: str):
        """
        解析llm的输出，提取Thought和Action
        """
        # Thought: 匹配到 Action: 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # Action: 匹配到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought_content = thought_match.group(1).strip() if thought_match else None
        action_content = action_match.group(1).strip() if action_match else None
        return thought_content, action_content
    

    def _parse_action(self, action_text: str):
        """
        解析Action字符串，提示调用的工具和工具输入参数
        """
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        
        return None, None

"""
ReAct范式智能体测试用例
"""
if __name__ == "__main__":
    ## 初始化LLM客户端
    llm_client = OpenAICompatibleClient()
    ## 初始化工具箱
    toolExecutor = ToolExecutor()
    ## 注册搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)
    ## ReAct范式智能体
    reActAgent = ReActAgent(llm_client, toolExecutor)
    reActAgent.run("华为最新的手机型号")
        