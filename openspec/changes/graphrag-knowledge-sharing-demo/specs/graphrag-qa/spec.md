## ADDED Requirements

### Requirement: 实体关系抽取

GraphRAG 程序 SHALL 用 LLM 从每篇语料文档抽取 `(subject, relation, object)` 三元组，关系 MUST 限定在固定集合内，抽取结果 MUST 缓存到磁盘（如 `graph.json`）。

#### Scenario: 抽取三元组并缓存
- **WHEN** 首次对语料运行 GraphRAG 程序
- **THEN** 程序逐篇文档抽取三元组、每条边记录来源文档，并将结果写入磁盘缓存

#### Scenario: 二次运行复用抽取结果
- **WHEN** 语料未变化时再次运行
- **THEN** 程序从缓存加载三元组，不重新调用抽取

### Requirement: 构建知识图

GraphRAG 程序 SHALL 将三元组构建为有向图（实体为节点，关系为边，边保留 `relation` 与 `source` 属性），并 MUST 能打印图的规模（节点数、边数）。

#### Scenario: 从三元组建图
- **WHEN** 三元组抽取完成
- **THEN** 程序构建有向图并打印节点与边的数量

#### Scenario: 边保留来源信息
- **WHEN** 检查图中任意一条边
- **THEN** 该边带有 `relation` 与来源文档 `source` 属性

### Requirement: 多跳图遍历检索

GraphRAG 程序 SHALL 从问题中识别起点实体，从起点在图上做限深多跳遍历，收集路径上的三元组作为上下文；对聚合类问题 MUST 支持"遍历某节点的一类邻居再逐个下钻"。

#### Scenario: 线性多跳遍历
- **WHEN** 向程序提出线性多跳问题 Q1
- **THEN** 程序从起点实体沿关系边逐跳遍历，收集完整链条 `公司→CEO→母校→城市` 的三元组作为上下文

#### Scenario: 聚合多跳遍历
- **WHEN** 向程序提出聚合问题 Q2
- **THEN** 程序遍历母公司的全部子公司、对每个子公司下钻其 CEO 与母校，并按城市过滤得到符合条件的人

### Requirement: 遍历过程可视化

GraphRAG 程序 SHALL 打印每一步中间结果，包括抽取的三元组、图规模、起点实体、逐跳访问序列与最终命中路径。

#### Scenario: 打印逐跳路径
- **WHEN** 程序对一个多跳问题执行遍历
- **THEN** 输出中依次展示每一跳访问的实体/关系，以及最终用于生成的完整路径

### Requirement: 正确回答传统 RAG 无法回答的问题

GraphRAG 程序 SHALL 使用与传统 RAG 相同的语料与问题，并在 Q1 与 Q2 上给出正确答案。

#### Scenario: 多跳问题答对
- **WHEN** 向 GraphRAG 程序提出 Q1
- **THEN** 程序基于遍历得到的完整链条给出正确的最终城市答案

#### Scenario: 聚合问题答对
- **WHEN** 向 GraphRAG 程序提出 Q2
- **THEN** 程序给出母校在指定城市的正确子公司 CEO
