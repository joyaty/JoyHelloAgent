
import os
from openai import OpenAI
from dotenv import load_dotenv

## 加载环境变量配置
load_dotenv()

class OpenAICompatibleClient:
    """
    兼容OpenAI接口的LLM服务客户端封装
    """

    def __init__(self, model: str = None, api_key: str = None, base_url: str = None, timeout: int = None):
        """
        构造函数，初始化LLM客户端。优先使用传入的参数，如果没有传入则从环境变量中读取配置。
        """
        self.model = model or os.getenv("LLM_MODEL_NAME")
        api_key = api_key or os.getenv("LLM_API_KEY")
        base_url = base_url or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT"))
        if not all([self.model, api_key, base_url, timeout]):
            raise ValueError("LLM模型配置不完整，请确保环境变量中包含LLM_MODEL_NAME、LLM_API_KEY、LLM_BASE_URL和LLM_TIMEOUT。")
        
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    
    def think(self, prompt: str, system_prompt: str, temperature: float = 0.0) -> str:
        """
        调用大语言模型进行思考，并返回其响应
        """
        print(f"正在调用{self.model}模型...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
            response = self.client.chat.completions.create(model=self.model, messages=messages, stream=True, temperature=temperature)
            print("大语言模型响应成功。")
            ## 处理流式响应
            collected_content = []
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                print(content, end="", flush=True)
                collected_content.append(content)
            print() # 流式输出结束后换行
            return "".join(collected_content)
        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误: 调用大语言模型时出错。"