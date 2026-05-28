---
name: operator-development
description: 当用户需要在 LPU/NPU/AI 加速器类项目中编写、开发、重构或修改 pymodel 算子时使用，包括确认计算图、规划 tile/buffer 数据流、实现算子指令流、生成 task bin、插入或检查 set_flag/wait_flag/fence、排查 cmodel sequential 与 full replay 不一致、定位 RTL/UVM replay/GM mismatch。适用于 prefill/decode attention、flash streaming、KV cache、GQA、RoPE、RMSNorm 等复杂算子实现和验证。
metadata:
  short-description: pymodel 算子开发、修改与 set-wait/fence 同步规范
---

# 算子开发与 set-wait 插入 Skill

本文档用于沉淀 pymodel 算子开发、task bin 生成、cmodel replay、RTL/UVM 调试过程中可复用的工作方法。重点是如何在实现算子时正确规划数据流，并插入合适的 `set_flag`、`wait_flag` 和 `fence`，使 pymodel、cmodel sequential replay、cmodel full replay 和 RTL UVM 的行为一致。

本文档以通用规范为主。QWen3 prefill attention 只作为典型复杂算子的案例，用来说明 flash streaming、KV cache、GQA、RoPE、RMSNorm 和多执行单元同步的处理方式。

## 1. 适用场景

适用于以下任务：

- 新增 pymodel 算子。
- 重构已有 pymodel 算子。
- 将一个算子从简单 functional flow 改成 tile/block 流水实现。
- 生成或更新 task bin。
- 修复 cmodel sequential replay 和 full replay 结果不一致。
- 修复 RTL UVM 中 cmodel check、top GM check、post-task replay check 不一致。
- 检查 `set_flag`、`wait_flag`、`fence` 是否缺失、冗余或 sync id 使用错误。

不适合直接用于以下情况：

- 算法 reference 本身尚未确认。
- 输入/输出 tensor layout 尚未确定。
- ISA 字段语义尚未明确。
- RTL 模块行为还没有基本验证。

这类情况要先把 reference、layout、ISA 语义确认清楚，再进入本 skill 的实现和同步阶段。

## 2. 总原则

先确认计算图，再写指令流。

先保证普通指令功能正确，再处理控制依赖。

先在 pymodel 中证明数据布局、地址、数值路径合理，再考虑修改 cmodel 或 RTL。

`set_flag` / `wait_flag` 用来保证跨执行单元的数据可见性和 buffer 复用安全。

`fence` 用来保证同一执行单元内部的顺序依赖，尤其是 ARU 内部依赖、MXU PSB 累加依赖。

不要通过随意修改 cmodel、RTL 或 ISA 实现来掩盖 pymodel 参数错误。只有确认 pymodel 生成的指令参数合理，并且 cmodel/RTL 行为与 ISA 语义不一致时，才修改 cmodel 或 RTL。

验证结果不能只说 pass。每次要报告 pymodel 误差、cmodel sequential replay、cmodel full replay、必要时 UVM 结果。

## 3. 开始修改前的检查

先确认目标算子的角色：

- 是 prefill、decode、training 还是普通 block op。
- 是否需要输出中间 cache。
- 是否需要支持 mask。
- 是否需要支持 GQA/MQA/MHA。
- 是否需要 RMSNorm、LayerNorm、RoPE、activation、residual add。
- 输出是否只有主结果，还是有多个输出，例如 `out`、`k_cache`、`v_cache`。

如果计算图、数据流、tile 切分、cache 语义或输出语义没有确认，不要直接开始改代码。此时应该先和使用者讨论并确认方案，至少把以下内容说清楚：

- 算子的输入、输出和中间 cache。
- 每个主要阶段的计算顺序。
- 是否需要保存中间结果到 GM。
- 哪些数据只在当前 tile 内临时使用。
- 是否需要 prefill/decode 这类阶段差异。
- 是否使用 flash streaming，还是先保存完整中间矩阵再做后续计算。
- GQA/MQA/MHA 的 head 映射关系。
- RMSNorm、RoPE、mask、residual add 等模型特定逻辑的位置。
- tile 大小和 buffer 复用策略。

只有使用者确认方案后，才进入具体实现。若实现过程中发现原方案与 ISA、buffer 容量、cmodel/RTL 行为冲突，也要先反馈新的约束和调整方案，再继续大改。

阅读已有实现：

- 当前目标文件。
- 同类算子的 pymodel 实现。
- 目标模型已有的 reference 实现。
- 更简单但数据流相似的算子。
- cmodel replay 测试。
- UVM task test。

常用搜索命令：

```bash
rg "op_name|target_function|TaskGen" /path/to/repo/pymodel
rg "op_name|target_test" /path/to/repo/cmodel /path/to/repo/rtl
rg "set_flag|wait_flag|fence" /path/to/repo/pymodel /path/to/repo/cmodel
```

如果是复杂算子，先写下数据流草图。至少明确：

- 每个 GM tensor 的 shape、dtype、layout。
- 每个 UB/LMB/RMB/PMB/PSB/ARB 临时 buffer 的用途。
- 每个 tile 的维度。
- 哪些 buffer 会被复用。
- 哪些执行单元会读写同一块数据。
- 哪些数据需要写回 GM。

## 4. 命名和文件组织

算子名称要表达真实阶段，不要使用过宽泛的名字。

示例：

- prefill attention 使用 `qwen3_prefill_attention`。
- decode attention 使用 `qwen3_decode_attention`。
- 不要继续保留容易混淆的旧别名，例如旧的 `qwen3_attention`。

文件组织建议：

- 主算子实现放在模型或 ops 对应目录下，例如 `pymodel/qwen3/prefill_attention.py`。
- golden reference 放在 `pymodel/ref/` 下。
- task bin 生成逻辑放在 `gen_taskbin.py`。
- 多输出比较逻辑放在 utils 中。
- 不要把 reference 函数直接塞进 task bin 生成脚本。

当旧实现已经不再使用时，删除 legacy 主体实现。不要在同一个文件里长期保留两个 attention 主体，否则后续维护者很容易误判当前路径。

## 5. 代码风格约束

### 5.1 Helper 函数

不要把简单的一两行逻辑过度包装成 helper 再调用。比如只服务当前位置的地址分配逻辑，可以直接内联。

可以保留有实际价值的 helper：

- 被多处复用。
- 封装复杂 layout 转换。
- 封装稳定的数值子流程。
- 能显著减少重复和错误。

删除 helper 前要确认不会降低可读性。原则是减少无意义跳转，而不是机械地把所有代码摊平。

### 5.2 ISA 调用

ISA 调用必须尽量使用 keyword 参数。不要用长位置参数。

不要写成：

```python
isa.aru_psb2ub(rope_psb, q_ub, None, 1, -np.inf, np.inf, 1, head_dim, q_size, head_n1, ub_row_m, 0, False, False)
```

应写成：

```python
isa.aru_psb2ub(psb_m1n1m0n0=rope_psb, ub_n1mn0=q_ub, clamp_min=None, clamp_max=None,
               slice_m=q_size, slice_n=head_dim, tile_m=ub_row_m, tile_n1=head_n1,
               start_tile_m=0, start_tile_n1=0, ub_wr_en=True, arb_wr_en=False)
```

### 5.3 参数排版

不要每个参数占一行。

推荐：

- 普通指令尽量一行。
- 参数特别多时拆成 2 到 3 行。
- 最多不要超过 3 行。
- keyword 参数必须保留语义清晰。

### 5.4 无关修改

不要顺手删除 cmodel/RTL 中已有的 debug print、verbose trace 或调试开关，除非用户明确要求。

不要顺手改 generated 文件、task bin、so、wave、log，除非当前任务需要。

不要为了让测试通过而放宽 tolerance，除非已经分析清楚误差来源，并且这种 tolerance 与硬件/数值格式一致。

## 6. Reference 和结果比较

golden reference 应该是简单、直接、可信的高层实现。优先用 PyTorch 或 NumPy 表达数学语义，而不是模拟底层 tile 指令。

多输出算子要同时比较所有关键输出。

示例：

```python
def compare_results(op, result, golden):
    if op == "qwen3_prefill_attention":
        out, k_cache, v_cache = result
        golden_out, golden_k_cache, golden_v_cache = golden
        return (
            torch.allclose(out.float(), golden_out.float(), atol=4e-2, rtol=0.1)
            and torch.allclose(k_cache.float(), golden_k_cache.float(), atol=4e-2, rtol=0.05)
            and torch.allclose(v_cache.float(), golden_v_cache.float(), atol=4e-2, rtol=0.05)
        )
    return compare(result, golden)
```

比较函数建议放在 utils 中，函数名使用通用语义，例如 `compare_results`。

报告误差时不要只报告 pass/fail。至少报告：

- max absolute error。
- max relative error。
- error percentage。
- 首个 mismatch 地址或 tensor index。
- 哪个输出失败，例如 `out`、`k_cache`、`v_cache`。

## 7. Tile 和 Buffer 规划

实现前要明确每个 tile 参数的含义。

常见命名：

- `seq_tile`：query 或 kv 的序列 block 大小。
- `head_tile`：head_dim 方向切分大小。
- `hidden_tile`：hidden_dim 方向切分大小。
- `out_hidden_tile`：输出 projection 的 hidden 方向切分大小。

示例：

```text
seq_tile = 32
head_tile = 32
hidden_tile = 256
out_hidden_tile = 128
```

含义可能是：

- 每次处理 32 个 token。
- 每次处理 head_dim 中 32 维。
- hidden_dim=1024 时，按 256 分 4 次累加 projection。
- output projection 根据 PSB/RMB/UB 容量按 128 维切分。

这些参数不是固定模板，必须根据 ISA layout、buffer 容量、PSB/RMB 形状和模型维度确认。

## 8. QWen3 Prefill Attention 示例计算流

QWen3-0.6B 的典型维度：

```text
hidden_dim = 1024
q_num_heads = 16
kv_num_heads = 8
head_dim = 128
q_output_dim = 2048
kv_output_dim = 1024
gqa_ratio = q_num_heads / kv_num_heads = 2
```

prefill attention 主流程：

1. 外层按 query head 遍历。
2. 取一块 `x_q`，例如 `(32, 1024)`，用于计算 Q。
3. 取一块 `x_kv`，例如 `(32, 1024)`，用于计算 K/V。
4. `x_q` 和 `x_kv` 在 projection 前都做 `input_layernorm_weight` RMSNorm。
5. hidden_dim 按 tile 切分，例如 `1024 = 4 * 256`。
6. 用 `x_q @ W_q` 得到当前 query head 的 Q。
7. 用 `x_kv @ W_k` 和 `x_kv @ W_v` 得到当前 kv head 的 K/V。
8. Q projection 后使用 `q_weight` 做 head_dim RMSNorm。
9. K projection 后使用 `k_weight` 做 head_dim RMSNorm。
10. Q/K RMSNorm 后做 RoPE。
11. K/V 写回 GM，形成 prefill 输出的 KV cache。
12. 当前 block 的 K/V 保留在 UB，立即参与当前 attention，避免从 GM 重新搬回。
13. 后续 query head 如果共享同一个 kv head，则直接复用已生成的 K/V cache。
14. context 计算完成后，与 `W_o` 相乘。
15. 最终结果与输入 `x` 做 residual add。

GQA 映射：

```text
kv_head = q_head // (q_num_heads // kv_num_heads)
```

例如 `q_num_heads=16`、`kv_num_heads=8` 时：

```text
q_head 0, 1  -> kv_head 0
q_head 2, 3  -> kv_head 1
...
q_head 14,15 -> kv_head 7
```

## 9. True Flash Streaming

prefill attention 应优先实现 true flash streaming，而不是保存完整 `P(32, seq_len)` 再统一做 PV。

每个 `kv_start` block 立即更新 streaming softmax 状态：

```text
score_block = Q_block @ K_block.T / sqrt(head_dim)
score_block += mask_block

m_new = max(m_old, rowmax(score_block))
p_block = exp(score_block - m_new)
o_acc = o_acc * exp(m_old - m_new) + p_block @ V_block
l = l * exp(m_old - m_new) + rowsum(p_block)
m = m_new
```

最终：

```text
context = o_acc / l
```

典型维度：

```text
Q_block:      (32, 128)
K_block:      (32, 128)
score_block:  (32, 32)
V_block:      (32, 128)
p_block @ V:  (32, 128)
```

如果 RMB/PSB 容量或 layout 不允许一次做完整 `(32,32) @ (32,128)`，可以把 V 的 head_dim 切成 4 次：

```text
p_block(32,32) @ V_part(32,32) -> o_acc_part(32,32)
```

这只是 buffer/layout 适配。主算法仍是每个 kv block 立刻更新 `m/l/o_acc`，不保存完整 P。

## 10. KV Cache 规则

prefill attention 中 K/V 有两个角色。

当前 block 的临时参与计算：

```text
K/V in UB -> QK/PV
```

prefill 输出的 cache：

```text
K/V in UB -> ub2gm -> GM KV cache
```

正确数据流是：

```text
projection -> q/k RMSNorm -> RoPE -> K/V in UB
K/V in UB -> ub2gm -> GM cache
K/V in UB -> 当前 QK/PV 计算
```

不要为了当前 attention 再把刚写入 GM 的 K/V 取回 UB。只要当前 UB 中的数据仍然有效，应直接复用。

如果后续 query block 或 GQA 共享 head 需要使用历史 K/V，则可以从 GM KV cache 读取。

## 11. RoPE 数据流注意事项

RoPE 本质是在 head_dim 的偶偶/奇奇配对维度上做旋转。

对单个 token、单个 head：

```text
k_before_rope: (128,)
rope cos/sin:  (64,)
k_after_rope:  (128,)
```

数学表达：

```text
even' = even * cos - odd * sin
odd'  = even * sin + odd * cos
```

如果实现使用矩阵形式，可以理解为：

```text
k_rotated[token] = k_before_rope[token] @ rope_matrix[token]
```

其中：

```text
k_before_rope[token]: (1, 128)
rope_matrix[token]:   (128, 128)
k_rotated[token]:     (1, 128)
```

实际实现通常不会显式存完整 `(128,128)` rope matrix，而是用 cos/sin 表和 ARU/MXU 指令完成等价旋转。

要区分：

- `k_block_ub`：当前刚算出来、还在 UB 的 K block。
- `k_cache_ub`：从 GM KV cache 搬回 UB 的历史 K。

如果当前 block 刚生成 K 并且仍在 UB，直接使用 `k_block_ub`。如果是后续 query block 需要历史 K，则使用 `k_cache_ub`。

## 12. Set-Wait 插入规则

先识别数据流，再分配 sync id。

`set_flag` 和 `wait_flag` 解决的是跨执行单元之间的生产者/消费者关系，以及 buffer 地址复用前的反向保护。

### 12.1 正常写后读

生产者写完数据后 `set_flag`，消费者读数据前 `wait_flag`。

常见关系：

```text
GDMA -> LDMA: GM 到 UB 后，LDMA 从 UB 搬到 LMB/RMB
GDMA -> MXU: GM 到 LMB/RMB 后，MXU 使用
LDMA -> MXU: UB 到 LMB/RMB 后，MXU 使用
MXU  -> ARU: MXU 写 PSB 后，ARU 从 PSB 读
ARU  -> LDMA/MXU/GDMA: ARU 写 UB 后，其他单元使用 UB
```

### 12.2 PSB 写后读和读后写

如果 MXU 写入某个 PSB 地址，后续 ARU 要从这个 PSB 地址搬到 UB/GM，则下一条复用同一 PSB 地址的 MXU 不能提前覆盖。

危险序列：

```text
MXU writes psb_A
ARU psb2ub reads psb_A
MXU writes psb_A again
```

必须保证：

```text
MXU writes psb_A
ARU drains psb_A
next MXU may reuse psb_A
```

这类依赖可能需要：

- MXU -> ARU 的正常 `set-wait`。
- ARU -> MXU 的反向 `set-wait`，保护 PSB 地址复用。

### 12.3 LMB/RMB 复用

如果 LMB/RMB 地址会环形复用，要保证 MXU 已经消费完旧数据后，LDMA/GDMA 才能覆盖。

危险序列：

```text
LDMA writes rmb_A
MXU reads rmb_A
LDMA writes rmb_A again
```

需要在地址复用前建立 MXU -> LDMA/GDMA 的同步。

通常在以下场景重点检查：

- lmb/rmb 数据超过 buffer 边界并绕回。
- 多个 matmul 使用相同 LMB/RMB 地址。
- GDMA 或 LDMA 搬运速度可能超过 MXU 消费速度。

### 12.4 UB 源数据复用

GDMA 可能比 LDMA 快。如果 LDMA 还没有从 UB 搬完，新的 GM2UB 已经覆盖同一 UB 地址，就会导致 LDMA 搬错数据。

危险序列：

```text
GDMA gm2ub writes ub_A
LDMA ub2lmb reads ub_A
GDMA gm2ub writes ub_A again
```

需要保证 LDMA 已经读走 UB 数据后，GDMA 才能复用同一 UB 地址。

### 12.5 ARU 依赖

ARU 指令之间如果存在数据依赖，要插入 `fence`。

例如：

```text
ARU psb2ub writes ub_A
ARU ub2ub reads ub_A
```

或：

```text
ARU dual2ub writes ub_A
ARU ub2gm reads ub_A
```

这类同执行单元依赖不能只靠跨单元 set-wait。

## 13. Fence 插入规则

`fence` 主要用于同一执行单元内部的顺序依赖。

### 13.1 ARU 内部依赖

如果后一条 ARU 指令读取前一条 ARU 指令的输出，需要 fence。

示例：

```text
aru_psb2ub -> aru_ub2ub
aru_ub2ub  -> aru_dual2ub
aru_dual2ub -> aru_ub2gm
```

### 13.2 MXU PSB 累加依赖

如果两个 matmul 使用相同 PSB 地址，并且后一条 `psum_en=True`，后一条 matmul 依赖前一条 matmul 留在 PSB 中的 partial sum。

示例：

```text
mxu_matmul(psb_A, psum_en=False)
mxu_matmul(psb_A, psum_en=True)
```

这类依赖应插入 fence 或等价的 MXU 内部顺序约束。

否则 parallel/full replay 可能在时序上暴露问题，而简单顺序执行不一定能发现。

### 13.3 不要用 fence 替代跨单元 set-wait

跨执行单元数据依赖应该用 `set_flag` / `wait_flag`。

同一执行单元内部顺序依赖才考虑 `fence`。

不要因为不想分配 sync id 就滥用 fence。

## 14. Sync ID 分配规则

### 14.1 同一种数据流复用同一个 id

同一对执行单元之间、同一种数据流可以使用同一个 id。

示例：

```text
MXU -> ARU: psb2ub ready
```

只要这些 transfer 不会并发混淆，可以统一使用同一个 id。

### 14.2 并发数据流使用不同 id

同一对执行单元之间如果存在多个并发数据流，必须使用不同 id。

例如 GDMA 和 MXU 之间可能同时有：

```text
GM -> LMB: x/q data
GM -> RMB: Wq
GM -> RMB: Wk
GM -> RMB: Wv
GM -> RMB: Wo
```

这些不能全部混用一个 id。否则某个 `wait_flag` 可能被错误的 `set_flag` 满足。

### 14.3 wait 必须对应正确 set

检查每个 `wait_flag`：

- 等待的 src/dst 是否与生产者一致。
- id 是否与对应数据流一致。
- 是否可能被同 id 的其他数据提前唤醒。
- 是否存在没有对应 set 的 wait。

检查每个 `set_flag`：

- 是否有真实消费者。
- 是否会被尾部遗留。
- 是否可能导致 count 和 wait 不一致。

### 14.4 id 数量有限

sync id 有最大值限制，通常按 16 个以内规划。

可以复用 id，但必须确认旧数据流已经完全结束，且不会和新数据流并发。

## 15. Trailing Sync 清理

最后一条有效数据指令之后，不应该残留没有消费者的 `set_flag` 或 `wait_flag`。

典型错误：

```text
...
aru_ub2gm final output
set_flag ...
wait_flag ...
```

如果 `ub2gm` 已经是最后的数据动作，后面的同步通常没有意义，还可能造成 replay 行为不一致。

清理 trailing sync 时要同时确认：

- `set_flag` 数量和 `wait_flag` 数量是否仍然一致。
- 每个 wait 都有对应 set。
- 每个 set 都有消费者。
- 没有死等。
- 没有为了 count 对齐而加入无意义 flag。

快速检查命令：

```bash
grep -c "set_flag" /path/to/op.ptx
grep -c "wait_flag" /path/to/op.ptx
grep -n "set_flag\\|wait_flag\\|aru_ub2gm" /path/to/op.ptx | tail -80
```

## 16. Sequential Replay 和 Full Replay

### 16.1 目标

理想情况下，cmodel sequential replay 和 full replay 的数值结果应该一致。

如果两者不一致，优先怀疑控制依赖：

- 缺少 set/wait。
- sync id 混用。
- PSB 被下一条 MXU 提前覆盖。
- LMB/RMB 被 LDMA/GDMA 提前覆盖。
- UB 被 GDMA 提前覆盖。
- ARU 内部缺 fence。
- MXU `psum_en` 依赖缺 fence。
- replay scheduler 没有正确模拟四个执行单元队列语义。

### 16.2 sequential 的语义

如果 sequential 只是把四个执行单元队列摊平成一个全局 instr_idx 序列，并且 `wait_flag` 不满足时也继续往下跑，这种 sequential 不能代表真实 set-wait 语义。

更合理的 sequential replay 应该是单线程 cooperative scheduler：

- GDMA、LDMA、MXU、ARU 仍各自保持队列顺序。
- 每次检查各队列队首。
- 普通指令可执行则执行。
- `wait_flag` 满足才弹出。
- `wait_flag` 不满足只阻塞当前队列头。
- `set_flag` 执行后唤醒对应依赖。

这样 sequential 和 full replay 才是在同一套控制语义下比较。

### 16.3 full replay 的语义

full replay 通常更接近并行执行：

- 多个执行单元可能并行推进。
- 搬运、计算和 ARU 操作会交叠。
- 缺失同步更容易暴露。

所以如果普通顺序看起来正确，但 full replay 错，重点查 buffer 复用和跨单元依赖。

## 17. 验证阶梯

根据当前修改范围选择验证层级。不要一开始就跑最慢的 UVM。

### 17.1 Python 编译检查

适用于修改 pymodel Python 文件后：

```bash
cd /path/to/repo/pymodel
python -m py_compile qwen3/prefill_attention.py
```

把路径替换为本次修改的目标文件。

### 17.2 pymodel 单测

适用于验证算子功能：

```bash
cd /path/to/repo/pymodel
python -m unittest test.BlockTestQWen.test_qwen3_prefill_attention
```

如果算子名字不同，替换测试类和测试函数。

### 17.3 task bin 生成

适用于验证 `gen_taskbin.py` 和 task 文件输出：

```bash
cd /path/to/repo/pymodel
python gen_taskbin.py qwen3_prefill_attention --seed 1 --out-dir /path/to/out --basename op_qwen3_prefill_attention
```

具体参数以当前脚本支持的 CLI 为准。先用 `python gen_taskbin.py --help` 确认。

### 17.4 cmodel replay

适用于检查 generated task bin 在 cmodel 中是否正确：

```bash
cd /path/to/repo/cmodel
./build_or_test_command_for_replay op_qwen3_prefill_attention
```

不同仓库的 cmodel test 命令可能不同。核心要求是分别覆盖：

- `execute_sequential()`。
- `execute()` full replay。
- `check_gm()`。

如果是 gtest，可以增加或运行类似测试：

```cpp
TEST_F(replay, op_qwen3_prefill_attention)
{
    lpu.load_task_bin("../func_tests/task_bin/op_qwen3_prefill_attention.bin");
    lpu.execute();
    EXPECT_TRUE(lpu.check_gm());
}
```

必要时增加 sequential 路径：

```cpp
TEST_F(replay, op_qwen3_prefill_attention_sequential)
{
    lpu.load_task_bin("../func_tests/task_bin/op_qwen3_prefill_attention.bin");
    lpu.execute_sequential();
    EXPECT_TRUE(lpu.check_gm());
}
```

### 17.5 多 seq_len 回归

对于 prefill 类算子，要覆盖边界长度。

建议：

```text
16, 31, 32, 33, 64, 127, 128, 129, 255, 256, 257, 512
```

如果随机配置支持：

```bash
for seed in 1 2 3 4 5; do
    python gen_taskbin.py qwen3_prefill_attention --seed ${seed}
done
```

还要记录每个 seed 对应的 `seq_len` 和误差。

### 17.6 UVM

适用于 cmodel 已经基本通过后，验证 RTL：

```bash
cd /path/to/repo/rtl/unit_test/lpu_uvm
make run TEST=lpu_qwen3_prefill_attention_task_test seed=1 PLUSARGS="+DUMP_DISPATCH_TASK +ENABLE_CMODEL_CHECK +ENABLE_TOP_GM_CHECK +ENABLE_POST_TASK_REPLAY_CHECK" LPU_REPLAY_VERBOSITY=detail
```

如果当前测试不是 QWen3 prefill attention，替换 `TEST` 和 task 名。

UVM 太慢时，先不要反复完整跑。优先看：

- generated `.ptx`。
- `run.log` 第一个 mismatch。
- cmodel replay 是否能复现。
- set/wait 数量和尾部同步。
- 关键 buffer 地址是否复用。
- 是否有旧 simv 进程还在跑。

## 18. cmodel so 和 RTL interface

修改 cmodel 后，如果 UVM 通过 DPI 调用 cmodel，要重新编译 `.so`，并放到 RTL interface 的 lib 目录。

典型位置：

```text
/path/to/repo/rtl/interface/lib
```

检查项：

- cmodel 源码已重新编译。
- 新 `.so` 时间戳是最新的。
- `rtl/interface` 中声明、wrapper、DPI bridge、头文件和构建脚本与 cmodel 导出接口一致。
- 如果 cmodel 的函数签名、导出符号、buffer 访问接口、compare 接口、replay 接口或配置参数发生变化，不只要更新 `.so`，还要同步更新 `rtl/interface` 下对应文件。
- 更新 `rtl/interface` 后要重新确认 UVM 编译时使用的是最新 interface 文件，而不是旧编译产物。
- UVM 使用的不是旧 `.so`。
- 没有旧 simv 进程继续占用旧环境。

查找旧进程：

```bash
ps -ef | rg "simv|lpu_qwen3_prefill_attention"
```

确认无用后再停止。

## 19. UVM Log 和 FSDB 调试

UVM 失败时先读 `run.log`，找第一个有效错误，不要从最后一屏开始猜。

常用命令：

```bash
rg -n "UVM_ERROR|UVM_FATAL|mismatch|Mismatch|ERROR|FATAL|check|GM|replay" /path/to/run.log
tail -200 /path/to/run.log
```

如果需要看波形：

```bash
xwave /path/to/lpu_tb.fsdb
```

UVM 出错时，不能只看 log 或只看波形。要把四类信息放在一起对齐：

- pymodel 生成的 `.ptx` / task bin，确认指令参数、地址、tile、set/wait/fence。
- cmodel sequential 和 full replay，确认普通指令语义和并行控制语义。
- RTL `run.log`，定位第一个 mismatch、fatal、timeout 或 replay check 失败点。
- xwave 打开的 FSDB 波形，确认真实 RTL dispatch、valid/ready、buffer 读写和 set/wait 时序。

波形中优先看：

- 出错前后的 instr_idx。
- dispatch task 顺序。
- 对应执行单元 valid/ready。
- buffer 地址。
- set/wait 状态。
- PSB/LMB/RMB/UB 写读是否重叠。
- cmodel 和 RTL 首个 mismatch 的 GM offset 对应哪个输出。

推荐定位顺序：

1. 从 `run.log` 找第一个有效错误，不要先看最后一个错误。
2. 把 mismatch 的 GM offset 映射到具体输出，例如 `out`、`k_cache`、`v_cache` 或中间 dump 区域。
3. 在 generated `.ptx` 中找到负责写该 GM 区间的指令和前后依赖。
4. 用 cmodel sequential/full replay 判断是普通指令问题还是并行依赖问题。
5. 用 xwave 在 FSDB 中查看相同 instr_idx 附近 RTL 是否按预期执行。
6. 如果 cmodel 正确但 RTL 错，重点查 RTL valid/ready、buffer 地址、mask、slice/tile 边界和 interface 参数传递。
7. 如果 cmodel 和 RTL 都错，优先回到 pymodel 指令参数和计算图。
8. 如果 sequential 正确但 full replay 或 RTL 错，优先查 `set_flag`、`wait_flag`、`fence` 和 buffer 复用。

如果 UVM 运行一次要数小时，先用更小 seq_len 或更小 task 复现。

## 20. generated task 和 git

task bin 可能被 `.gitignore` 忽略。

如果确实需要提交：

```bash
git add -f cmodel/func_tests/task_bin/op_qwen3_prefill_attention.bin
```

但 generated bin 一般要谨慎提交。优先确认项目规范。

本地有未提交修改且远端有新提交时，不要直接 `git pull` 覆盖。可选：

```bash
git status
git stash push -u -m "wip before pull"
git pull --rebase
git stash pop
```

或先提交本地修改：

```bash
git add <files>
git commit -m "..."
git pull --rebase
```

有冲突时按文件解决，不要用 `git reset --hard` 丢弃本地工作，除非明确确认。

## 21. 常见问题定位

### 21.1 pymodel pass，cmodel sequential fail

优先检查：

- task bin 是否最新。
- GM 初始化是否一致。
- output GM 地址是否正确。
- dtype/bfloat16 转换是否一致。
- cmodel ISA 实现是否支持当前参数组合。
- pymodel 是否使用了 cmodel 不支持的 layout。

### 21.2 sequential pass，full replay fail

优先检查：

- 缺少跨单元 set/wait。
- sync id 混用。
- PSB/LMB/RMB/UB 地址复用。
- ARU/MXU fence 缺失。
- 最后一段 trailing sync。
- wait/set 数量是否失衡。

### 21.3 sequential 和 full replay 误差不一致

优先比较：

- 两者首个 GM mismatch offset。
- mismatch offset 属于 out、k_cache 还是 v_cache。
- 产生该 GM 区间的 instr_idx。
- 对应 ptx 前后的 set/wait/fence。
- 是否存在 full replay 中提前覆盖 buffer。

### 21.4 UVM 比 cmodel 更差

优先检查：

- UVM 是否加载了最新 task bin。
- RTL interface 是否加载了最新 cmodel `.so`。
- cmodel check tolerance 是否合理。
- RTL 是否支持当前 ISA 参数。
- generated ptx 是否有 RTL 不支持的边界参数。
- 是否存在 valid/ready 背压导致的实际执行顺序暴露同步问题。

### 21.5 怀疑 RTL 错误

先证明 pymodel 参数合理。

例如不要直接修改 LDMA RTL 来支持一个可疑参数组合。先检查：

- `tile_m`、`slice_m`、`start_tile_m` 是否合理。
- slice 是否越过 tile 边界。
- mask 是否应该由 MXU/ARU 生效。
- LDMA 搬运窗口和 MXU 实际计算窗口是否被混淆。

LDMA 搬了多行不代表 MXU 会计算所有行。MXU 是否只使用有效行，要看 MXU 指令的 `slice_m`、`slice_n` 和内部实现。

## 22. 报告模板

每次完成一个算子修改，建议按以下格式汇报：

```text
修改内容:
- <文件1>: <核心变化>
- <文件2>: <核心变化>

pymodel:
- seed=<seed>, seq_len=<seq_len>
- out max_abs=<...>, max_rel=<...>, error=<...>%
- k_cache max_abs=<...>, max_rel=<...>, error=<...>%
- v_cache max_abs=<...>, max_rel=<...>, error=<...>%

cmodel sequential:
- pass/fail
- first mismatch=<...> 或 error=<...>%

cmodel full replay:
- pass/fail
- first mismatch=<...> 或 error=<...>%

sync:
- set_flag count=<...>
- wait_flag count=<...>
- ids=<...>
- trailing sync: yes/no

UVM:
- command=<...>
- pass/fail/not run
- first error=<...>
```

如果某项没有运行，明确写 `not run`，并说明原因。

## 23. Anti-patterns

不要在没确认计算图时直接改指令流。

不要把 reference 写进 task bin 生成脚本。

不要保留废弃 alias 和 legacy 主实现。

不要用长位置参数调用 ISA。

不要每个参数独占一行导致指令不可读。

不要为了临时通过而随意放宽 tolerance。

不要让 `set_flag` 和 `wait_flag` 尾部残留。

不要把不同并发数据流混用一个 sync id。

不要只跑 sequential replay 就认为 full replay 一定正确。

不要在 UVM 很慢时反复盲跑。先用 generated ptx、cmodel replay、小 seq_len 和首个 mismatch 定位。

不要未经确认修改 cmodel/RTL 通用行为。

不要删除用户需要保留的 debug print 或 verbose trace。
