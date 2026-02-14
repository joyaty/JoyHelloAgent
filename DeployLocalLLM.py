"""
部署本地LLM模型，使用Qwen1.5-0.5B-Chat模型，验证分词器和语言模型的工作情况
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

## 指定模型ID
model_id = "Qwen/Qwen1.5-0.5B-Chat"
## 设置部署的设备平台，如果有GPU则使用GPU，否则使用CPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
## 加载分词器和模型，并将模型移动到指定设备上
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id).to(device)
print("分词器和模型加载完成！")

## 准备对话输入
message = [
    {"role": "system", "content": "你是我的人工智能助手，协助我解答问题。"},
    {"role": "user", "content": "你好，请介绍一下你自己。"}
]
## 使用分词器的模板格式化输入  
text = tokenizer.apply_chat_template(message, tokenize=False, add_generation_prompt=True)
## 编码输入文本并打印
model_inputs = tokenizer([text], return_tensors="pt").to(device)
print(f"编码后的输入文本:{model_inputs}, 输入文本的token数量: {model_inputs.input_ids.shape[1]}")

## 使用模型生成回答
## max_new_tokens参数指定模型最多能生成多少个新的token，这里设置为512，表示模型可以生成最多512个新的token作为回答。
generated_ids = model.generate(model_inputs.input_ids, max_new_tokens=512)
## 将生成的TokenID截取掉输入部分，这样我们只解码模型新生成的部分，得到模型的回答文本。
generated_ids = [
    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
] 
## 解码生成的TokenID，得到模型的回答文本，并打印出来。skip_special_tokens=True参数表示在解码时跳过特殊的token（如[CLS]、[SEP]等），只保留模型生成的实际文本内容。
response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(f"模型回答: {response}")