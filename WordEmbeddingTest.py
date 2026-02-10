"""
词向量测试代码示例，使用简单的二维向量来演示词向量之间的关系。
真实大语言模型中，词向量可能是几十或上百维的高维向量。
"""

import numpy as np

## 定义一些简单的词向量，实际应用中这些向量会通过训练得到
vector_groups = {
    "king": np.array([0.9, 0.8]),
    "queen": np.array([0.9, 0.2]),
    "man": np.array([0.7, 0.9]),
    "woman": np.array([0.7, 0.3])
}

## 通过计算余弦来表示两个词向量的相似度
def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    return dot_product / (norm_vec1 * norm_vec2)

## 表示king-man+woman的向量关系
ret_vec = vector_groups["king"] - vector_groups['man'] + vector_groups['woman']
## 结果向量与queen的相似度
similarity_scores = cosine_similarity(ret_vec, vector_groups['queen'])

print(f"king - man + woman 的结果向量为: {ret_vec}")
print(f"queen向量为: {vector_groups['queen']}")
print(f"结果向量与queen的余弦相似度为: {similarity_scores}")