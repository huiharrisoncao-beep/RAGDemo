"""基准问题（Q1 线性多跳 / Q2 聚合多跳），中英双语 + 标准答案。

两个程序（RAG/ 与 GraphRAG/）共用这里的问题，保证对比公平。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Question:
    qid: str
    text: str
    kind: str  # "linear" | "aggregate"
    start_entities: List[str]  # 图遍历起点实体（GraphRAG 用）
    expected_keywords: List[str] = field(default_factory=list)  # 判定答对的关键词


QUESTIONS = {
    "cn": {
        "Q1": Question(
            qid="Q1",
            text="云枢智能的CEO毕业于哪所大学？那所大学在哪个城市？",
            kind="linear",
            start_entities=["云枢智能"],
            expected_keywords=["未名理工大学", "江城"],
        ),
        "Q2": Question(
            qid="Q2",
            text="星环科技旗下所有子公司的CEO里，谁的母校在江城？",
            kind="aggregate",
            start_entities=["星环科技"],
            expected_keywords=["李明"],
        ),
    },
    "en": {
        "Q1": Question(
            qid="Q1",
            text="From which university did the CEO of Yunshu Intelligence graduate, "
            "and in which city is that university located?",
            kind="linear",
            start_entities=["Yunshu Intelligence"],
            expected_keywords=["Weiming Institute of Technology", "Jiangcheng"],
        ),
        "Q2": Question(
            qid="Q2",
            text="Among the CEOs of all subsidiaries of Xinghuan Technology, "
            "whose alma mater is located in Jiangcheng?",
            kind="aggregate",
            start_entities=["Xinghuan Technology"],
            expected_keywords=["Li Ming"],
        ),
    },
}


def get_questions(lang: str) -> "dict[str, Question]":
    return QUESTIONS[lang]
