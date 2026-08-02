"""基准问题（Q1 线性多跳 / Q2 聚合多跳），中英双语 + 标准答案。

两个程序（RAG/ 与 GraphRAG/）共用这里的问题，保证对比公平。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List


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


_UI = {
    "cn": {
        "banner": "进入循环问答模式：直接输入问题，或用快捷键选择预备问题。",
        "preset": "预备问题",
        "quit_hint": "退出",
        "prompt": "请输入问题（或输入 1/2 选择预备问题，q 退出）> ",
        "picked": "已选择",
        "bye": "已退出，再见。",
    },
    "en": {
        "banner": "Interactive Q&A mode: type a question, or use a shortcut to pick a preset.",
        "preset": "preset question",
        "quit_hint": "quit",
        "prompt": "Enter a question (or 1/2 to pick a preset, q to quit) > ",
        "picked": "Picked",
        "bye": "Bye.",
    },
}


def run_interactive(lang: str, ask: Callable[[str], None]) -> None:
    """循环问答：用户输入问题即作答；输入 1/2 选择预备问题；输入 q 退出。

    ask: 接受问题文本并完成一次问答的回调。
    """
    ui = _UI.get(lang, _UI["cn"])
    presets = list(get_questions(lang).values())

    print("\n" + "=" * 70)
    print(ui["banner"])
    for i, q in enumerate(presets, 1):
        print(f"  [{i}] {ui['preset']} {q.qid}: {q.text}")
    print(f"  [q] {ui['quit_hint']}")
    print("=" * 70)

    while True:
        try:
            raw = input("\n" + ui["prompt"]).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n" + ui["bye"])
            break
        if not raw:
            continue
        if raw.lower() in ("q", "quit", "exit"):
            print(ui["bye"])
            break
        if raw.isdigit() and 1 <= int(raw) <= len(presets):
            question = presets[int(raw) - 1].text
            print(f"{ui['picked']}: {question}")
        else:
            question = raw
        ask(question)
