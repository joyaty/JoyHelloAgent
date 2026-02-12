"""
Byte Pair Encoding (BPE) 是一种基于统计的文本分词方法，常用于自然语言处理任务中。它通过迭代地合并最频繁出现的符号对来构建一个新的词表，从而实现对文本的有效编码。
"""

import re, collections

def get_stats(vocab):
    """
    作用：在当前词表上统计所有相邻符号对（bigram）的出现次数（按词频加权）。
    约定：vocab 的 key 是已用空格分开的符号序列（如 'h u g </w>'），value 是词频。
    返回：一个字典，键为 (symbol_i, symbol_i+1)，值为该对在所有词中的总出现次数。
    """
    pairs = collections.defaultdict(int) 
    for word, freq in vocab.items():
        symbols = word.split()
        for i in range(len(symbols) - 1):
            pairs[symbols[i], symbols[i + 1]] += freq
    return pairs

def merge_vocab(pair, v_in):
    """
    作用：把指定的符号对在整个词表中合并成一个新符号（去掉中间空格）。
    实现：用正则把 "a b" 形式的片段替换成 "ab"，且只在「完整符号边界」上替换（避免误合并），得到新词表 v_out，并保持原词频。
    效果：合并后，原先的二元组在词表表示里变成一个新 token（例如 u g → ug）。
    """
    v_out = {}
    bigram = re.escape(' '.join(pair))
    p = re.compile(r"(?<!\S)" + bigram + r"(?!\S)")
    for word in v_in:
        w_out = p.sub(''.join(pair), word)
        v_out[w_out] = v_in[word]
    return v_out

## 准备语料库，每个词末尾加上</w>表示结束，并切分好字符
vocab = {'h u g </w>': 1, 'p u g </w>': 1, 'p u n </w>': 1, 'b u n </w>': 1}
## 设置合并次数
num_merges = 4

for i in range(num_merges):
    pairs = get_stats(vocab)
    if not pairs:
        break
    best = max(pairs, key = pairs.get)
    vocab = merge_vocab(best, vocab)
    print(f"第{ i + 1 }次合并: { best } -> { ''.join(best) }")
    print(f"新词表(部分)： {list(vocab.keys())}")
    print("-" * 20)
