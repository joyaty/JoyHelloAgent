
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START, END

from tavily import TavilyClient
from dotenv import load_dotenv

import os
import asyncio

## 加载配置
load_dotenv()

## 初始化LLM客户端
llm = ChatOpenAI(
    model = os.getenv("LLM_MODEL_NAME"),
    api_key = os.getenv("LLM_API_KEY"),
    base_url = os.getenv("LLM_BASE_URL"),
    temperature = 0.7 
)
## 初始化Tavily搜索工具客户端
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

class SearchState(TypedDict):
    """
    LangGraph的全局状态上下文
    """
    messages: Annotated[list, add_messages]
    user_query: str             # 用户查询原始文本
    search_query: str           # AI优化后的精准查询文本
    search_result: str          # Tavily工具的搜索结果
    final_answer: str          # 最终呈现给用户的结果
    step: str                   # 当前的步骤

def understand_query_node(state: SearchState) -> SearchState:
    """步骤1: 理解用户查询并生成搜索关键词"""
    # 获取用户输入的消息
    user_message = ""
    for msg in reversed(state['messages']):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break
    understand_prompt = f"""
分析用户的查询："{user_message}"

请完成两个任务：
1. 简洁总结用户想要了解什么
2. 生成最适合搜索的关键词（中英文均可，要精准）

格式：
理解：[用户需求总结]
搜索词：[最佳搜索关键词]

"""
    response = llm.invoke([HumanMessage(content = understand_prompt)])
    # 提取搜索关键词
    response_text= response.content
    search_query = user_message # 默认使用原始查询
    if "搜索词：" in response_text:
        search_query = response_text.split("搜索词：")[1].strip()
    elif "搜索关键词：" in response_text:
        search_query = response_text.split("搜索关键词：")[1].strip()

    return {
        "user_query": response.content,
        "search_query": search_query, 
        "step": "understood",
        "messages": [AIMessage(content=f"我理解您的需求：{response.content}")]
    }


def tavily_search_node(state: SearchState) -> SearchState:
    """步骤2：使用Tavily API进行真实搜索"""
    search_query = state["search_query"]
    try:
        print(f"🔍 正在搜索: {search_query}")
        # 调用Tavily搜索API执行搜索
        response = tavily_client.search(
            query = search_query,
            search_depth = "basic",
            include_answer = True,
            include_raw_content = False,
            max_results = 5
        )
        # 处理搜索结果
        search_results = ""
        # 优先使用Tavily的综合答案
        if response.get("answer"):
            search_results = f"综合答案：\n{response['answer']}\n\n"
        # 添加具体的搜索结果
        if response.get("results"):
            search_results += "相关信息：\n"
            for i, result in enumerate(response["results"][:3], 1):
                title = result.get("title", "")
                content = result.get("content", "")
                url = result.get("url", "")
                search_results += f"{i}. {title}\n{content}\n来源：{url}\n\n"
        
        if not search_results:
            search_results = "抱歉，没有找到相关信息。"
        
        return {
            "search_result": search_results,
            "step": "searched",
            "messages": [AIMessage(content=f"✅ 搜索完成！找到了相关信息，正在为您整理答案...")]
        }
    except Exception as e:
        error_msg = f"搜索时发生错误: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "search_result": f"搜索失败：{error_msg}",
            "step": "search_failed",
            "messages": [AIMessage(content="❌ 搜索遇到问题，我将基于已有知识为您回答")]
        }
    
def generate_answer_node(state: SearchState) -> SearchState:
    """步骤3：基于搜索结果生成最终答案"""
    # 搜索工具异常处理
    if state["step"] == "search_failed":
        fallback_prompt = f"""
搜索API暂时不可用，请基于您的知识回答用户的问题：

用户问题：{state['user_query']}

请提供一个有用的回答，并说明这是基于已有知识的回答。
"""
        # 调用大模型生成最终答案
        response = llm.invoke([SystemMessage(content = fallback_prompt)])
        return {
            "messages": [AIMessage(content = response.content)],
            "final_answer": response.content,
            "step": "completed"
        }
    
    answer_prompt = f"""
基于以下搜索结果为用户提供完整、准确的答案：

用户问题：{state['user_query']}

搜索结果：
{state['search_result']}

请要求：
1. 综合搜索结果，提供准确、有用的回答
2. 如果是技术问题，提供具体的解决方案或代码
3. 引用重要信息的来源
4. 回答要结构清晰、易于理解
5. 如果搜索结果不够完整，请说明并提供补充建议
"""
    response = llm.invoke([HumanMessage(content=answer_prompt)])
    return {
        "messages": [AIMessage(content = response.content)],
        "final_answer": response.content,
        "step": "completed" 
    }

def create_search_assistant():
    """创建搜索AI助手"""
    workflow = StateGraph(SearchState)
    # 添加三个节点
    workflow.add_node("understand", understand_query_node)
    workflow.add_node("search", tavily_search_node)
    workflow.add_node("answer", generate_answer_node)
    # 设置线性流程
    workflow.add_edge(START, "understand")
    workflow.add_edge("understand", "search") 
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)
    # 编译图
    memory = InMemorySaver()
    app = workflow.compile(checkpointer = memory)

    return app


async def main():
    """主函数：运行智能搜索助手"""
    app = create_search_assistant()
    print("🔍 智能搜索助手启动！")
    print("我会使用Tavily API为您搜索最新、最准确的信息")
    print("支持各种问题：新闻、技术、知识问答等")
    print("(输入 'quit' 退出)\n")
    session_count = 0
    while True: 
        user_input = input("🤔 您想了解什么: ").strip()
        ## 检测用户是否退出
        if user_input.lower() in {'quit', 'q', '退出', 'exit'}:
            print("感谢使用！再见！👋")
            break
        if not user_input:
            continue

        ## 初始上下文状态
        initial_state = {
            "messages": [HumanMessage(content = user_input)],
            "user_query": "",
            "search_query": "",
            "search_result": "",
            "final_answier": "",
            "step": "start"
        }

        session_count += 1
        config = {"configurable": {"thread_id": f"search-session-{session_count}"}}

        try:
            print("\n" + "=" * 60)
            ## 执行工作流
            async for output in app.astream(input = initial_state, config = config):
                for node_name, node_output in output.items():
                    if "messages" in node_output and node_output["messages"]:
                        latest_message = node_output["messages"][-1]
                        if isinstance(latest_message, AIMessage):
                            if node_name == "understand":
                                print(f"🧠 理解阶段: {latest_message.content}")
                            elif node_name == "search":
                                print(f"🔍 搜索阶段: {latest_message.content}")
                            elif node_name == "answer":
                                print(f"\n💡 最终回答:\n{latest_message.content}")

            print("\n" + "=" * 60 + "\n")
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            print("请重新输入您的问题。\n")

if __name__ == "__main__":
    asyncio.run(main())