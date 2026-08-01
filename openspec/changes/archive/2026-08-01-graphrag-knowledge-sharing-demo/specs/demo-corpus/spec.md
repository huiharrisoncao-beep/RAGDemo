## ADDED Requirements

### Requirement: 双语平行语料目录结构

系统 SHALL 在 `Docs/cn/` 与 `Docs/en/` 下提供文件名一一对应的平行语料，程序 MUST 能通过 `CORPUS_LANG`（`cn` | `en`）选择语料目录。

#### Scenario: 中英文件一一对应
- **WHEN** 检查 `Docs/cn/` 与 `Docs/en/` 目录
- **THEN** 两个目录包含相同的文件名集合（如 `companies.md`、`leadership.md`、`people.md`、`universities.md`、`investors.md`），且每对文件描述同一批实体与关系

#### Scenario: 按配置选择语料语言
- **WHEN** 设置 `CORPUS_LANG=en` 并运行任一问答程序
- **THEN** 程序读取 `Docs/en/` 下的语料而非 `Docs/cn/`

### Requirement: 多跳事实跨文档拆散

语料 SHALL 将每条多跳推理链的相邻两跳事实放置在不同的文档中，且每篇文档 MUST NOT 出现其下一跳的关键实体名称，从而使扁平相似度召回无法在单次检索中获取完整链条。

#### Scenario: 线性多跳链条被拆散
- **WHEN** 追踪主链「公司 → CEO → 母校 → 城市」
- **THEN** 「公司↔子公司」事实在 `companies.md`、「谁任 CEO」在 `leadership.md`、「CEO 母校」在 `people.md`、「母校所在城市」在 `universities.md`，且各文档不含相邻跳的关键实体关键词

#### Scenario: 单文档不足以回答多跳问题
- **WHEN** 只阅读任意一篇语料文档
- **THEN** 该文档无法独立回答线性多跳问题 Q1，必须跨多篇文档串联

### Requirement: 支持聚合多跳查询的语料

语料 SHALL 包含支撑聚合类多跳查询所需的事实（一个母公司拥有多个子公司、各子公司有各自 CEO、各 CEO 有各自母校与城市），使得回答需要"遍历 + 过滤"。

#### Scenario: 聚合查询所需事实齐备
- **WHEN** 追踪聚合题 Q2「某母公司旗下所有子公司的 CEO 里，谁的母校在某城市」
- **THEN** 语料中存在该母公司的多个子公司、每个子公司对应的 CEO、每个 CEO 对应的母校及其城市，足以完成遍历与按城市过滤

### Requirement: 固定关系集合与可翻译实体命名

语料中的关系 SHALL 落在预定义集合内（子公司、CEO、毕业于、位于、投资），实体命名 MUST 采用中英可对照的名称，以保证抽取稳定且双语图结构一致。

#### Scenario: 关系落在固定集合内
- **WHEN** 人工或程序抽取语料中的三元组
- **THEN** 每个关系都属于 {子公司, CEO, 毕业于, 位于, 投资} 之一

#### Scenario: 实体中英可对照
- **WHEN** 比较 `Docs/cn` 与 `Docs/en` 中同一实体
- **THEN** 存在稳定的中英名称对应（如「云枢智能」↔「Yunshu Intelligence」）
