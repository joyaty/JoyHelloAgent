
import requests
import os
import re
from dotenv import load_dotenv
from tavily import TavilyClient
from OpenAICompatibleClient import OpenAICompatibleClient

"""
    通过调用wttr.in API查询真实的天气信息
"""
def Get_Weather(city:str) -> str:
    # 拼接查询http请求
    url = f"http://wttr.in/{city}?format=j1"

    try:
        # 发起网络请求
        response = requests.get(url)
        # 检查响应状态码是否为200 (请求成功)
        response.raise_for_status()
        # 解析返回的json数据
        data = response.json()
        # 提取当前的天气信息，格式化为自然语言
        current_condition = data["current_condition"][0]
        weather_desc = current_condition["weatherDesc"][0]["value"]
        tempture_c = current_condition["temp_C"]
        return f"{city}当前天气:{weather_desc}, 气温{tempture_c}摄氏度"
    except requests.exceptions.RequestException as e:
        return f"错误:查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        return f"错误:解析天气数据失败，可能时城市名称无效 - {e}"

"""
    通过Tavily API查询资讯
"""
def Get_Attraction(city: str, weather: str) -> str:
    # 从环境变量获取API密钥
    api_key = os.getenv("TAVILY_API_KEY")
    # 初始化Tavily客户端
    tavily = TavilyClient(api_key=api_key)
    # 3. 构造一个精确的查询
    query = f"'{city}'在'{weather}'天气下最值得去的旅游景点推荐及理由"

    try:
        # 4. 调用API，include_answer=True会返回一个综合性的回答
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        # 5. Tavily返回的结果已经非常干净，可以直接使用。response['answer'] 是一个基于所有搜索结果的总结性回答
        if response.get("answer"):
            return response.get("answer")
        # 如果没有综合性回答，则格式化原始结果
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result["title"]}: {result["content"]}")
        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"
        
        return "根据搜索，为您找到以下信息:\n" + "\n".join(formatted_results)
    except Exception as e:
        return f"错误:执行Tavily搜索时出现问题-{e}"
    
AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市和天气搜索推荐的旅游景点。

# 输出格式要求:
你的每次回复必须严格遵循以下格式，包含一对Thought和Action：

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一：
1. 调用工具：function_name(arg_name="arg_value")
2. 结束任务：Finish[最终答案]

# 重要提示:
- 每次只输出一对Thought-Action
- Action必须在同一行，不要换行
- 当收集到足够信息可以回答用户问题时，必须使用 Action: Finish[最终答案] 格式结束

请开始吧！
"""

# 将所有工具函数放入一个字典，方便后续调用
available_tools = {
    "get_weather": Get_Weather,
    "get_attraction": Get_Attraction,
}

"""
    基于Thought-Action-Observation范式设计的智能体循环
"""
def TravelAgentLoop(city: str):
    # 1. 初始化
    llm = OpenAICompatibleClient()
    user_prompt = f"你好，请帮我查询一下今天{city}的天气，然后根据天气推荐一下合适的旅游景点。"
    prompt_histories = [f"用户请求:{user_prompt}"]
    print(f"用户输入:{user_prompt}\n" + "="*40)

    # 2. 运行主循环
    for i in range(5): # 设置最大循环次数
        print(f"---- 循环 {i+1} ---- \n")
        # 2.1 构建prompt
        full_prompt = "\n".join(prompt_histories)
        # 2.2 调用LLM进行思考
        llm_output = llm.think(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
        match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
        if match:
            truncated = match.group(1).strip()
            if truncated != llm_output.strip():
                llm_output = truncated
                print("已截断多余的 Thought-Action 对")
        print(f"模型输出:\n{llm_output}\n")
        prompt_histories.append(llm_output)
        # 2.3 解析并且执行行动
        action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误：未能解析到Action字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "="*40)
            prompt_histories.append(observation_str)
            continue
        action_str = action_match.group(1).strip()

        if action_str.startswith("Finish"):
            final_answer = re.match(r"Finish\[(.*)\]", action_str, re.DOTALL).group(1)
            if not final_answer is None:
                print(f"任务完成，最终答案: {final_answer}")
            else:
                print(f"任务完成，最终答案(未格式): {action_str}")
            break

        tool_name = re.search(r"(\w+)\(", action_str).group(1)
        args_str = re.search(r"\((.*)\)", action_str).group(1)
        kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

        if tool_name in available_tools:
            observation = available_tools[tool_name](**kwargs)
        else:
            observation = f"错误:未定义的工具 '{tool_name}'"

        # 2.4. 记录观察结果
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "="*40)
        prompt_histories.append(observation_str)

if __name__ == "__main__":
    # 加载.env项目环境变量
    load_dotenv()
    # # 使用wttr.in API查询天气
    # ret_weather = Get_Weather("乌鲁木齐")
    # print(ret_weather)
    # # 使用Tavily搜索信息
    # ret_search = Get_Attraction("厦门", "雨天")
    # print(ret_search)
    # 测试Thought-Action-Observation范式的智能体循环
    TravelAgentLoop("新疆")