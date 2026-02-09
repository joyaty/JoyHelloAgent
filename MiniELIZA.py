"""
MiniELIZA: 类ELIZA规则的聊天机器人，基于模式匹配和文本替换的符号主义智能体
支持简单的上下文记忆：记住用户提到的姓名、性别、职业等信息。
"""

import re
import random

# ---------- 上下文记忆 ----------
# 用户信息存储：key 为槽位名，value 为用户说过的内容
user_memory = {}

# 记忆提取规则：(正则, 记忆槽位名)。匹配到则把捕获组写入对应槽位
memory_extraction_rules = [
    (r"(?:my name is|i'm called|call me|you can call me)\s+([^.?!]+)", "name"),
    (r"(?:i work as|i am a|i'm a)\s+([^.?!]+)", "occupation"),
    (r"i (?:am|'m) (male|female|a man|a woman|boy|girl)\b", "gender"),
    (r"(?:i live in|i'm from)\s+([^.?!]+)", "location"),
]

def extract_memory(user_input: str) -> None:
    """从用户输入中抽取关键信息并写入 user_memory。"""
    text = user_input.strip()
    if not text:
        return
    for pattern, slot in memory_extraction_rules:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                user_memory[slot] = value

def get_memory_context() -> dict:
    """返回当前记忆的副本，便于在回复中使用。"""
    return dict(user_memory)

# 定义规则库:模式(正则表达式) -> 响应模板列表
rules = {
    r"I need (.*)": [
        "Why do you need {0}?",
        "Would it really help you to get {0}?",
        "Are you sure you need {0}?"
    ],
    r"Why don't you (.*)\?": [
        "Do you really think I don't {0}?",
        "Perhaps eventually I will {0}.",
        "Do you really want me to {0}?"
    ],
    r"Why can't I (.*)\?": [
        "Do you think you should be able to {0}?",
        "If you could {0}， what would you do?",
        "I don't know -- Why can't you {0}?"
    ],
    r"I am (.*)": [
        "Did you come to me because you are {0}?",
        "How long have been {0}?",
        "How do you feel about being {0}?"
    ],
    r".* mother .*": [
        "Tell me about your mother.",
        "What was you relationship with your mother like?",
        "How do you feel about your mother?"
    ],
    r".* father .*": [
        "Tell me more about your father.",
        "How did your father make you feel?",
        "What has your father taught you?"
    ],
    r".*": [
        "Please tell me more.",
        "Let's change focus a bit... Tell me about your family.",
        "Can you elaborate on that?"
    ]
}

# 定义代词转换规则
pronoun_swap = {
    "i": "you", "you": "i", "me": "you", "my": "your",
    "am": "are", "are": "am", "was": "were", "i'd": "you would",
    "i've": "you have", "i'll": "you will", "yours": "mine",
    "mine": "yours"
}

"""
对输入短语中的代词进行第一/第二人称转换
"""
def swap_pronouns(phrase: str):
    words = phrase.lower().split()
    swapped_words = [pronoun_swap.get(word, word) for word in words]
    return " ".join(swapped_words)

"""
根据规则库生成响应
"""
def respond(user_input):
    for pattern, responses in rules.items():
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            # 捕获匹配到的部分
            captured_group = match.group(1) if match.groups() else ""
            # 进行代词转换
            swapped_group = swap_pronouns(captured_group)
            # 从模板中随机选择一个并格式化
            response = random.choice(responses).format(swapped_group)
            return response
    # 如果没有匹配任何特定规则，使用最后的通配符规则
    return random.choice(rules[r".*"])


def personalize(response: str) -> str:
    """在回复中融入已记住的用户信息（如称呼名字），使对话更自然。"""
    name = user_memory.get("name", "").strip()
    if name and random.random() < 0.4:  # 40% 概率在句首加上称呼
        return f"{name}, {response[0].lower()}{response[1:]}"
    return response

# 主聊天循环
if __name__ == "__main__":
    print("MiniELIZA: Hello! How can I help you today?")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            name = user_memory.get("name", "")
            goodbye = f"Goodbye, {name}. It was nice talking to you." if name else "Goodbye. It was nice talking to you."
            print(f"MiniELIZA: {goodbye}")
            break
        if user_input.strip().lower() in ["what do you know about me?", "你记住了什么", "你还记得什么"]:
            if not user_memory:
                print("MiniELIZA: I don't remember anything specific yet. Tell me your name or what you do!")
            else:
                parts = [f"You told me: {k} = {v}" for k, v in user_memory.items()]
                print("MiniELIZA: " + "; ".join(parts))
            continue
        extract_memory(user_input)   # 先尝试从本轮输入中抽取并记住信息
        response = respond(user_input)
        response = personalize(response)
        print(f"MiniELIZA: {response}")