## ADDED Requirements

### Requirement: 原理讲解内容

讲解材料 SHALL 分别说明传统 RAG 与 GraphRAG 的实现原理，并 MUST 使用图示（如 ASCII 图）呈现两者的数据流。

#### Scenario: 覆盖两种原理
- **WHEN** 阅读讲解材料
- **THEN** 材料包含传统 RAG 流程（embedding → 向量库 → top-k → 拼接生成）与 GraphRAG 流程（抽取 → 建图 → 图遍历 → 生成）的说明与图示

### Requirement: GraphRAG 优势阐述

讲解材料 SHALL 阐述 GraphRAG 的优势，MUST 至少覆盖多跳推理、跨文档串联、聚合查询、可解释路径、抗幻觉，并说明各自能解决什么问题。

#### Scenario: 列举并解释优势
- **WHEN** 阅读优势章节
- **THEN** 每项优势都配有它能解决的问题场景说明

### Requirement: 贯穿式对比案例

讲解材料 SHALL 包含一个与 Demo 一致的对比案例，MUST 展示传统 RAG 为何失败、GraphRAG 如何一步步做到，且案例问题 MUST 与 Demo 程序中的 Q1/Q2 相同。

#### Scenario: 案例与 Demo 对齐
- **WHEN** 对照讲解材料中的案例与 Demo 程序
- **THEN** 案例所用问题与语料与 `RAG/`、`GraphRAG/` 程序实际运行的一致

#### Scenario: 讲清"怎么做到"
- **WHEN** 阅读对比案例
- **THEN** 材料展示传统 RAG 的召回缺口，并逐跳展示 GraphRAG 在图上的遍历路径如何补全链条

### Requirement: 运行说明

材料 SHALL 提供根 `README.md`，说明依赖安装、环境变量配置（chat 与 embedding）、如何分别运行两个程序并进行并排对比。

#### Scenario: 按 README 可复现运行
- **WHEN** 新用户按照 `README.md` 配置环境变量并安装依赖
- **THEN** 能够成功运行 `RAG/` 与 `GraphRAG/` 程序并复现对比结果
