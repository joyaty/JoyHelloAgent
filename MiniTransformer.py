"""
实现 Transformer（“Attention Is All You Need”）中的核心子模块：位置编码、多头注意力、前馈层、编码器层、解码器层。

1. PositionalEncoding（位置编码）
作用：给序列中每个位置的嵌入向量加上“位置信息”，让模型知道词的顺序。
实现要点：
 - 预计算一个形状为 (max_len, d_model) 的矩阵，偶数维用 sin、奇数维用 cos，频率随维度变化。
 - 通过 register_buffer 保存，不参与训练但会随模型 to(device)。
 - forward：取与当前序列长度对应的那一段位置编码，加到输入 x 上，再做 dropout。
输入/输出：输入 (batch, seq_len, d_model)，输出形状不变

2. MultiHeadAttention（多头注意力）
作用：实现缩放点积多头注意力，可作自注意力或交叉注意力。
实现要点：
 - 用 W_q / W_k / W_v 得到 Q、K、V，再按头数切分为多份（split_heads）。
 - Scaled dot-product attention：softmax(QK^T / √d_k) @ V，支持可选的 mask（0 位置在 softmax 前被置为极小值）。
 - 多头结果拼回（combine_heads）后经 W_o 线性变换输出。
约束：d_model % num_heads == 0。
入参：query, key, value 及可选的 mask。

3. PositionWiseFeedForward（位置前馈网络）
作用：对每个位置独立做两层线性 + 激活，即 Transformer 中的 FFN 子层。
结构：Linear(d_model → d_ff) → ReLU → Dropout → Linear(d_ff → d_model)
输入/输出：形状均为 (batch, seq_len, d_model)，只在最后一维上做变换。

4. EncoderLayer（编码器层）
作用：Transformer 编码器的单层：一层自注意力 + 一层前馈，均带残差和 LayerNorm。
结构：
 - 多头自注意力：self_attn(x, x, x, mask) → 残差 + LayerNorm（norm1）。
 - 位置前馈：feed_forward(x) → 残差 + LayerNorm（norm2）。
构造：正确传入 d_model, num_heads, d_ff, dropout 给 MultiHeadAttention 和 PositionWiseFeedForward。
输入：x（编码器该层输入）、mask（如 padding mask）。

5. DecoderLayer（解码器层）
作用：Transformer 解码器的单层：自注意力（带因果/掩码）→ 交叉注意力（看编码器）→ 前馈，每步后残差 + LayerNorm。
结构：
 - 掩码多头自注意力：self_attn(x, x, x, tgt_mask)，用于解码器自身序列（常带因果 mask）→ 残差 + norm1。
 - 交叉注意力：cross_attn(x, encoder_output, encoder_output, src_mask)，以解码器当前表示为 Q，编码器输出为 K/V → 残差 + norm2。
 - 位置前馈：feed_forward(x) → 残差 + norm3。
构造：自注意力、交叉注意力和前馈均正确传入 d_model, num_heads, d_ff, dropout。
输入：x（解码器该层输入）、encoder_output、src_mask、tgt_mask。


PositionalEncoding     → 为序列加位置信息（通常用于 Encoder/Decoder 最前）
MultiHeadAttention     → 自注意力 / 交叉注意力的通用实现
PositionWiseFeedForward → 每位置的 FFN
EncoderLayer           → 自注意力 + FFN（各带残差+Norm），可堆叠成完整 Encoder
DecoderLayer           → 自注意力 + 交叉注意力 + FFN（各带残差+Norm），可堆叠成完整 Decoder
"""

import torch
import torch.nn as nn
import math

class PositionalEncoding(nn.Module):
    """
    为输入序列的词嵌入向量添加位置编码
    """
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 5000):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        ## 创建一个足够长的位置编码矩阵
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        ## pe(positional encoding)的大小为(max_len, d_model)
        pe = torch.zeros(max_len, d_model)
        ## 偶数维度使用sin，奇数维度使用cos
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        # 将pe注册为buffer，这样它就不会被视为模型参数，但会随模型移动（例如to(device)）
        self.register_buffer('pe', pe.unsqueeze(0))

    def forward(self, x) -> torch.Tensor:
        # x.size(1)是当前输入的序列长度
        # 将位置编码加到输入向量上
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)

class MultiHeadAttention(nn.Module):
    """
    多头注意力机制模块
    """
    def __init__(self, d_model, num_heads):
        super(MultiHeadAttention, self).__init__()
        assert d_model % num_heads == 0, "d_model 必须能被 num_heads 整除"
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        ## 定义Q,K,V和输出的线性变换层
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)

    def scaled_dot_product_attention(self, Q, K, V, mask = None):
        ## 1. 计算注意力得分(QK^T)
        attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        ## 2. 应用掩码(如果提供)
        if mask is not None:
            ## 将掩码中为0的位置设置为一个非常小的负数，这样softmax后会接近与0
            attn_scores = attn_scores.masked_fill(mask == 0, -1e-9)
        ## 3. 计算注意力权重(softmax)
        attn_probs = torch.softmax(attn_scores, dim=-1)
        ## 4. 加权求和(权重 * V)
        output = torch.matmul(attn_probs, V)
        return output

    def split_heads(self, x):
        ## 将输入x的形状(batch_size, seq_length, d_model)变换为(batch_size, num_heads, seq_length, d_k)
        batch_size, seq_length, d_model = x.size()
        return x.view(batch_size, seq_length, self.num_heads, self.d_k).transpose(1, 2)
    
    def combine_heads(self, x):
        ## 将输入x的形状从(batch_size, num_heads, seq_length, d_k)变换回(batch_size, seq_length, d_model)
        batch_size, num_heads, seq_length, d_k = x.size()
        return x.transpose(1, 2).contiguous().view(batch_size, seq_length, self.d_model)

    def forward(self, query, key, value, mask):
        ## 1. 对Q, K, V 进行线性变换
        Q = self.split_heads(self.W_q(query))
        K = self.split_heads(self.W_k(key))
        V = self.split_heads(self.W_v(value))
        ## 2. 计算缩放点积注意力
        attn_output = self.scaled_dot_product_attention(Q, K, V, mask)
        ## 3. 合并多头输出并进行最终的线性变换
        output = self.W_o(self.combine_heads(attn_output))
        return output 

class PositionWiseFeedForward(nn.Module):
    """
    位置前馈网络模块
    """
    def __init__(self, d_model, d_ff, dropout = 0.1):
        super(PositionWiseFeedForward, self).__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.dropout = nn.Dropout(dropout)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.relu = nn.ReLU()

    def forward(self, x):
        # x的形状：（batch_size, seq_len, d_model）
        x = self.linear1(x)
        x = self.relu(x)
        x = self.dropout(x)
        x = self.linear2(x)
        ## 最终输出形状：(batch_size, seq_len, d_model)
        return x

# --- 编码器核心层 ---
class EncoderLayer(nn.Module):
    """
    编码器核心层
    """
    def __init__(self, d_model, num_heads, d_ff, dropout):
        super(EncoderLayer, self).__init__()
        self.self_attn = MultiHeadAttention(d_model, num_heads)
        self.feed_forward = PositionWiseFeedForward(d_model,d_ff, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask):
        ## 1. 多头自注意力
        attn_output = self.self_attn(x, x, x, mask)
        x = self.norm1(x + self.dropout(attn_output))
        ## 2. 位置前馈网络
        ff_output = self.feed_forward(x)
        x = self.norm2(x + self.dropout(ff_output))
        return x

# --- 解码器核心层 --- 
class DecoderLayer(nn.Module):
    """
    解码器核心层
    """
    def __init__(self, d_model, num_heads, d_ff, dropout):
        super(DecoderLayer, self).__init__()
        self.self_attn = MultiHeadAttention(d_model, num_heads)
        self.cross_attn = MultiHeadAttention(d_model, num_heads) 
        self.feed_forward = PositionWiseFeedForward(d_model, d_ff, dropout)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout) 

    def forward(self, x, encoder_output, src_mask, tgt_mask):
        ## 1. 掩码多头自注意力(对自己)
        attn_output = self.self_attn(x, x, x, tgt_mask)
        x = self.norm1(x + self.dropout(attn_output))
        ## 2. 交叉注意力(对编码器输出)
        cross_attn_output = self.cross_attn(x, encoder_output, encoder_output, src_mask)
        x = self.norm2(x + self.dropout(cross_attn_output))
        ## 3. 位置前馈网络
        ff_output = self.feed_forward(x)
        x = self.norm3(x + self.dropout(ff_output))

        return x