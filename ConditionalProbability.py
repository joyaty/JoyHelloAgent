"""
最大似然估计计算(条件概率)，Bigram模型示例(N=2)
"""

import collections

## 示例语料库
corpus = "datawhale agent learns datawhale agent works" 
## 分割为词元表
tokens = corpus.split()
total_tokens = len(tokens)

## --- 第一步: 计算P(datawhale) ---
count_datawhale = tokens.count("datawhale")
p_datawhale = count_datawhale / total_tokens
print(f"第一步: P(datawhale) = {count_datawhale}/{total_tokens} = {p_datawhale:.4f}")

## --- 第二步: 计算P(agent|datawhale) ---
bigrams = zip(tokens, tokens[1:])
bigram_counts = collections.Counter(bigrams)
count_datewhale_agent = bigram_counts[("datawhale", "agent")]
p_agent_given_datawhale = count_datewhale_agent / count_datawhale
print(f"第二步: P(agent|datawhale) = {count_datewhale_agent}/{count_datawhale} = {p_agent_given_datawhale:.4f}")

## --- 第三步: 计算P(learns|agent) ---
count_agent_learns = bigram_counts[("agent", "learns")]
count_agent = tokens.count("agent")
p_learns_given_agent = count_agent_learns / count_agent
print(f"第三步: P(learns|agent) = {count_agent_learns}/{count_agent} = {p_learns_given_agent:.4f}")

## --- 第四步: 计算P(datawhale agent learns) ---
p_sentense = p_datawhale * p_agent_given_datawhale * p_learns_given_agent
print(f"最后: P(datawhale agent learns) = P(datawhale) * P(agent|datawhale) * P(learns|agent) = {p_datawhale:.4f} * {p_agent_given_datawhale:.4f} * {p_learns_given_agent:.4f} =  {p_sentense:.4 f}")
