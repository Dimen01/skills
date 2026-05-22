---
name: ai-paper-zh
description: Use when revising Chinese theses or papers in AI systems, AI chips, compilers, computer architecture, or systems engineering for contribution framing, abstract/introduction logic, related-work positioning, method/evaluation chapter organization, natural academic Chinese, figure/table prose, reference-thesis structure, bilingual abstracts, bibliography/format checks, or text that is AI-like, too low-level, code-like, obscure, or not human-written.
---

# AI Paper Zh

## Core Principle

Revise as a thesis coauthor, not as a sentence polisher. First fix the level of abstraction and the contribution story, then rewrite local sentences, then verify the delivered output in its actual format.

The recurring target style is: clear research problem, concrete gap, what this thesis did, what ability/result it produced. Avoid writing the thesis as a compressed implementation log.

For AI-chip, compiler, architecture, and systems work, keep the argument at the level of abstraction, constraints, method, tool flow, and measured capability. Separate algorithm semantics, program representation, compiler/runtime mapping, hardware/platform constraints, and implementation/verification artifacts instead of mixing them in one paragraph.

## Workflow

1. Read the active source and deliverable structure before editing.
   - Find the master document, included chapters/sections, bibliography sources, image/table sources, exported output, and any local instructions.
   - Determine which files actually affect the user-visible document. Do not spend edits on unused files unless the user asks or stale text may be reintroduced later.

2. Build the current story before touching prose.
   - Identify the thesis object: workload/problem, platform/system, abstraction or method, evaluation setup, and claimed result.
   - Locate abstract, introduction, contribution list, related work, chapter roadmaps, conclusion, and relevant figure/table captions.
   - If using a reference thesis, extract its table of contents and section roles first, then map those roles to the current thesis's own concepts. Do not import topic content or domain wording.
   - If the user provides meeting notes or advisor feedback, extract reusable requirements rather than paraphrasing the transcript.

3. Revise from high level to low level.
   - Abstract first: use the five-part pattern below.
   - Introduction next: make paragraph first sentences carry the same logic as the abstract.
   - Related work next: move from "existing work exists" to "classification axes -> existing foundations and gaps -> the thesis's own workflow or capability map."
   - Method chapters last: keep technical details where they explain the method, but make the chapter structure carry `background/challenge -> overall framework -> core method -> evaluation -> chapter summary`.

4. Verify after every meaningful edit set using the document's actual format.
   - Regenerate or export the user-visible deliverable when the format requires it.
   - Check the format-appropriate build/export diagnostics; do not assume the project is LaTeX.
   - Confirm the revised wording appears in the user-visible output, not only in source files.
   - Inspect layout-sensitive pages or objects visually when the user mentioned tables, figures, pagination, captions, or "looks bad".
   - If the generated output is separate from the user-facing file, sync it according to the project's convention.

## Abstraction Level Control

Use a pyramid of detail. The same method should be described at different levels in different places:

- Abstract, introduction, and conclusion: research problem, why hard, what existing work lacks, what capability the thesis builds, what the evaluation shows. Avoid backend interfaces, verification infrastructure, code fields, module names, and implementation errands.
- Chapter roadmap and first-chapter figures: show the thesis flow and responsibility split. Do not put low-level debug terms, file/interface names, or too many internal components in the opening figure.
- Method sections: define formal objects, constraints, algorithms, models, and implementation structure only when they directly explain the method.
- Experiment sections: give concrete settings, candidates, metrics, and result interpretation. Define comparison objects before comparing them.

For introduction prose, make each paragraph's first sentence carry the main claim. The first several paragraph claims should expand the abstract's logic rather than starting a separate story.

When advisor or meeting feedback is available, translate the feedback into rules, not transcript paraphrases. If the user's oral explanation is clearer than the draft, preserve the oral logic and rewrite it into academic Chinese. Common moves:

- "This is too low-level" means move details from abstract/introduction/conclusion into method, experiment, appendix, or omit them.
- "This is not human language" means replace label-like phrases with the concrete action or object they denote.
- "This comparison is confusing" means name the two comparison objects separately before stating which result is better.
- "The figure is too detailed" means redraw or rewrite around top-level flow: problem/object -> expression/model -> platform/constraint -> evaluation/result.

## Domain-General Argument Pattern

For AI systems, AI chips, compilers, computer architecture, and systems engineering, convert implementation details into a layered research story:

```text
workload or system problem
-> why existing algorithms/tools/platforms are insufficient
-> abstraction, representation, model, or workflow introduced by this work
-> generation, optimization, verification, or mapping method
-> platform-aware evaluation and measured capability
```

Keep these layers distinct:

- Algorithm or workload semantics: what must remain equivalent or correct.
- Program representation or system abstraction: how the thesis describes the problem space.
- Optimization or generation method: how designs, schedules, mappings, or configurations are produced.
- Platform or architecture constraints: what memory, compute, communication, parallelism, synchronization, or deployment constraints matter.
- Implementation and verification artifacts: scripts, simulators, RTL hooks, drivers, logs, and test harnesses. These usually belong in method details, appendices, or experiment setup, not in the abstract or opening motivation.

Common contribution axes in this area:

- Abstraction/model: formalizes a workload, execution process, memory behavior, dataflow, mapping, or hardware constraint.
- Search/generation/optimization: produces valid candidates, schedules, mappings, code, configurations, or design points.
- Analysis/evaluation: estimates cost, checks correctness, explains bottlenecks, or compares alternatives.
- System integration: connects layers of a toolchain or hardware/software stack when that integration creates a research capability, not merely an implementation pipeline.

Common evaluation claims:

- Correctness or equivalence: generated results preserve required semantics or interface behavior.
- Coverage or expressiveness: the method represents more workloads, patterns, mappings, or constraints.
- Performance, cost, or resource result: latency, throughput, energy, memory traffic, area, utilization, compile/search time, or deployment cost.
- Ablation or attribution: which part of the abstraction, model, optimization, or platform correction causes the result.
- Model accuracy: estimates match simulator, hardware, trace, or baseline measurements within stated scope.

## Abstract Pattern

Use this five-part structure for Chinese and English abstracts:

1. What this thesis studies.
2. Why the problem is difficult.
3. What existing work can do and what remains insufficient.
4. What this thesis does to solve it.
5. What the experiments/results show, with honest scope qualifiers.

Keep the abstract at the highest abstraction level. Do not insert implementation interfaces, verification environments, field names, low-level modules, or backend plumbing unless they are the actual thesis contribution.

Good method-level phrasing:

```text
本文从问题建模、设计空间表达和平台评估三个层面给出方法。
```

Too low-level for an abstract:

```text
后续连接仿真后端、验证环境和底层接口脚本。
```

When the user says "this should say how I solve it", avoid turning the abstract into a chapter inventory. Phrase the solution as a chain of capabilities:

```text
首先，建立用于约束设计空间的执行模型；其次，将这些约束融入中间表示、调度表达或映射描述，使设计点能够生成、检查和导出；最后，构建面向目标平台的评估方法，用于筛选可行方案并比较代价。
```

If a phrase like "在相同的问题规模和后端评估流程下" still feels stiff in an abstract, prefer a natural scope phrase such as:

```text
在本文的测试条件下
```

Put the detailed problem size and evaluation process in the experiment chapter.

## Contribution Framing

Avoid defensive or assembly-like framing:

```text
本文不是替代某类方法，而是把 A、B、C 统一到同一框架中。
```

Prefer gap-to-capability framing:

```text
已有工作为 A、B、C 提供了基础，但尚难直接支撑 X 问题中的生成、判断和比较。针对这一问题，本文建立 ...，使 ... 能够 ...
```

A strong contribution sentence should answer:

- Existing foundation: prior work already provides what.
- Remaining limitation: what is still hard in this thesis setting.
- Thesis capability: what new model/expression/evaluation/check is formed.
- Observable result: what can now be generated, screened, compared, or explained.
- Domain layer: whether the contribution is about semantics, representation, optimization, mapping, platform constraints, or evaluation evidence.

Do not overuse vague nouns such as `增量`, `衔接`, `统一框架`, `平台感知补偿`, `能力边界`, `分析依据`. If used, immediately say what concrete capability they produce.

## Human Academic Chinese

When the user says text is "AI 味", "不像人话", "晦涩", or "太底层", diagnose which failure it is:

- Obscure nominalization: replace abstract nouns with concrete actions.
- Code translation: replace field names and underscores with thesis concepts.
- Over-compression: split one dense claim into what is compared, under what condition, and what changes.
- Low-level leakage: move implementation details out of abstract/introduction/conclusion.
- Defensive framing: say what the thesis does instead of what it is not.

Use these replacement patterns:

| Avoid | Prefer |
| --- | --- |
| 中间结果物化 | 中间结果的写回、读取；中间结果被单独写出后再读回 |
| 外溢回填 | 超出容量的数据写出并在后续重新读取；容量越界补偿 |
| 语义保持不变 | 保持计算结果等价；保持接口行为一致 |
| 某某维、某某侧、某某阶段 | 写成具体对象：输入长度、输出通道、时间步、batch、tile 行/列、数据产生/消费位置 |
| 程序返回码为 0 | usually omit from thesis prose |
| `*_level`, `*_deps`, `resident_*`, `mapping/arch` | 融合或调度层级、依赖关系、驻留数据、映射方案、平台描述 |
| `某模型风格基线 + 平台感知补偿` | 先说明基准模型估计什么，再说明哪些平台代价被补入 |

Avoid raw code identifiers, monospaced formatting, and literal field names in Chinese thesis prose unless the identifier itself is a formal artifact under discussion. Keep mathematical symbols and defined method names where they are necessary.

## Reference Thesis Logic

When the user asks to learn from another thesis, extract only organization logic, section function, and rhetorical moves. Do not copy topic-specific wording, examples, technical claims, figure content, or domain framing. Translate the structure into the current thesis's own objects.

The reusable pattern learned from the reference thesis previously used for this project is:

```text
Introduction contribution story
-> related work as classification and positioning
-> method chapters with local evaluation
-> conclusion by the same contribution axes
```

Use this as a structural template, not as source content.

### Reference Extraction Protocol

Before using a reference thesis:

1. Extract the table of contents and major section headings with the file-appropriate extractor or the existing extracted text.
2. Label every section by role: background, challenge, classification axis, method overview, core abstraction, integration, experiment, summary, conclusion, future work.
3. Build a role map from reference thesis sections to current thesis sections. For example, "reference related-work closure" may map to the current thesis's final related-work section even if the titles differ.
4. Rewrite using only the role map. If a sentence depends on the reference thesis's topic, it should not be transferred.
5. After restructuring, check chapter numbers, roadmap text, cross-references, figure/table numbering, and conclusion references.

### Introduction And Contributions

Use this shape for the first chapter:

```text
research background and challenge
-> research motivation
-> main contributions and their relationships
-> thesis organization
```

The contribution section should first recap the challenges and motivation, then say that the thesis's contributions correspond to those challenges. Each contribution should contain four parts:

- research object or abstraction;
- proposed framework, method, or model;
- capability enabled by that method;
- evaluation result or observable effect.

Do not write contributions as a list of modules implemented. Use a relationship figure or table when there are multiple contribution axes. The figure/table should show how challenges, contributions, chapters, and evaluation evidence correspond.

The organization section should state the overall reading order first, then give a concise chapter roadmap. Each chapter description should explain its role in the argument, not summarize internal implementation details.

### Related Work Closure

Do not let the related-work chapter end as a literature catalog. Use this progression:

```text
announce classification dimensions
-> review work by those dimensions
-> identify which foundations are useful and which gap remains
-> present the thesis's own abstraction, workflow, or capability map
```

Useful dimensions include technique route, system layer, development stage, hardware/software boundary, task type, evaluation target, or capability requirement. Choose dimensions that help the current thesis argue for its method; do not import dimensions from the reference thesis unless they fit.

End the chapter with a section that bridges to the method chapters. The closure should answer:

- What common abstraction or problem formulation the thesis will use.
- How the next chapters divide responsibilities.
- Why the thesis's workflow follows from the related-work gaps.

When useful, include a compact table with columns like `分类维度 / 已有基础 / 仍难支撑的问题 / 本文处理方式`.

### Method Chapter Template

For each method chapter, prefer this order unless the current thesis has a strong reason to differ:

```text
chapter intro: where this chapter sits in the whole thesis
-> technical background and concrete challenge
-> overall framework or structure
-> core abstraction/model/method
-> analysis, optimization, generation, verification, or integration
-> experiment/evaluation results
-> chapter summary
```

The chapter intro should connect to the previous chapter or the thesis-wide workflow, then preview the chapter's abstraction and framework before details. It should not start with code-level implementation facts.

The `overall framework` section should appear before deep technical sections when the chapter has multiple moving parts. It gives readers a map: inputs, outputs, main components, and how the components support the chapter's research question.

If a method chapter depends on another layer or chapter, include an integration section near the end of the method explanation, before experiments. Its job is to show how the method fits the whole thesis, not to dump interface details.

### Experiment-In-Chapter Pattern

When the thesis has several distinct methods, consider putting experiments inside each method chapter rather than using one late standalone experiment chapter. Use the reference pattern:

```text
实验评估结果
-> 实验设置条件
-> result subsections grouped by the chapter's claims
-> interpretation of why the result changes
```

This is especially useful when each chapter makes a separate methodological claim and needs immediate evidence. It avoids making the reader wait until a final experiment chapter to see whether the method works.

Only fold a standalone experiment chapter into method chapters after checking:

- whether each method chapter has enough evaluation material;
- whether chapter count and roadmap text must change;
- whether conclusion and abstract refer to a separate experiment chapter;
- whether figure/table numbering and labels remain correct.

Experiment prose should state the evaluation question first, then settings, then results. Do not only report numbers. Explain which part of the method causes the difference and what the result does or does not prove.

### Chapter Summary And Conclusion

End each method chapter with a compact `本章小结`. The summary should say:

```text
this chapter targeted which problem
-> proposed which abstraction/method/framework
-> enabled which capability
-> experiments showed which result within what scope
```

Do not introduce new technical material in `本章小结`.

The final chapter should reuse the same contribution axes established in the introduction. Summarize by contribution or chapter role, then discuss future work at the level of research directions, unresolved limitations, and external trends. Avoid ending with backend interface work, file-format cleanup, or implementation errands unless those are truly thesis-level future work.

## Figures And Tables

Treat figures/tables as part of the argument.

- A page containing only one table or with an orphaned caption is a layout problem, not just a source-format problem.
- If a table is meant to compare contribution, prefer columns like `问题维度 / 已有基础与不足 / 本文工作` over vague "existing work can do / thesis adds".
- If table headers are visually off, check both horizontal and vertical alignment in the rendered output, not only the source table definition.
- If numeric differences matter, show enough decimals to make the claim visible, but do not overstate small differences.
- If a figure's axis or label says one thing and the surrounding paragraph says another, update the figure labels or the paragraph so they match.

For tables that must stay near explanatory text, use the local document pattern for keeping captions and table bodies together. After changes, inspect the rendered page to catch caption/body splits.

## Format And Bibliography Checks

For format-review tasks:

- Convert/extract requirement documents safely; do not edit thesis files unless asked.
- Report as `needs change`, `passes`, and `cannot judge automatically`.
- Exclude front matter the user explicitly says they will add later.
- Check page count, blank pages, page numbering, chapter starts, Chinese/English abstracts, table/figure captions, references, and format-specific warnings.

For bibliography:

- Compare citations that appear in the user-visible document with bibliography entries available to the document.
- Account for inactive chapters, hidden sections, appendices, and format-specific "include all references" settings.
- Report unused, missing, and visibly unresolved references separately.

## Completion Checklist

Before saying the revision is done:

- Source search shows disliked phrases are gone or intentionally retained.
- Chinese abstract and English abstract are aligned in meaning and abstraction level.
- Chapter roadmap, chapter count, labels, and references match the current structure.
- The document has been regenerated/exported when needed, and the command or tool completed successfully.
- Format-specific diagnostics show no new unresolved references, citation issues, export failures, or layout warnings that affect the requested work.
- Extracted text, rendered preview, or direct document inspection confirms the revised wording appears in the user-visible document.
- Layout-sensitive pages or objects have been checked visually when the user mentioned tables, figures, pagination, captions, or "looks bad".
