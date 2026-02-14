
from serpapi import SerpApiClient
import os
from typing import Dict, Any

def search(query: str) -> str:
    """
    一个基于SerpApi的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回直接答案或知识图谱信息。
    """
    print(f"正在执行[Serpapi]网页搜索")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误: SERPAPI_API_KEY未在.env文件中配置"
        
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn", # 国家代码
            "hl": "zh-cn", # 语言代码
        }
        ## 调用SerpApi搜索
        client = SerpApiClient(params)
        results = client.get_dict()
        ## 智能解析: 优先寻找最直接的答案
        if "answer_box_list" in results:
            return "\n".join(results['answer_box_list'])
        if "answer_box" in results and "answer" in results['answer_box']: # Goole的答案摘要框
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]: # 知识图谱
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            snippets = [
                f"[{i + 1}] {res.get('title', '')} \n {res.get('snippet', '')}" for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)
    except Exception as e:
        return f"执行搜索时发生错误:{e}"
    
class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}  ## Dict[str, Any] = {"description":description, "func":callable}

    def registerTool(self, name: str, description: str, func: callable):
        """
        向工具箱注册一个新工具
        """
        if name in self.tools:
            print(f"警告：工具'{name}'已存在，将被覆盖")
        self.tools[name] = {"description": description, "func":func}
        print(f"工具'{name}'注册成功") 
    
    def getTool(self, name: str) -> callable:
        """
        获取工具的可调用对象
        """
        return self.tools.get(name, {}).get("func")
    
    def getAvailableToolsDesc(self) -> str:
        """
        获取可调用工具的列表描述
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])

"""
工具箱测试单元测试
""" 
if __name__ == "__main__":
    ## 初始化工具箱
    toolExecutor = ToolExecutor()
    ## 注册搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)
    ## 打印工具箱中可用的工具
    print("\n---------可用的工具----------")
    print(toolExecutor.getAvailableToolsDesc())
    # 测试调用工具箱中的工具
    tool_name = "Search"
    tool_input = "英伟达最新的GPU型号是什么"
    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误: 未找到名为{tool_name}的工具。")
        