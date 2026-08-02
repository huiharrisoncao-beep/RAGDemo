"""手写轻量 GraphRAG 问答程序（教学向，三步透明）。

流程：
  ① 抽取  每篇文档 --LLM--> (subject, relation, object) 三元组（固定关系集）
  ② 建图  三元组 --networkx--> 有向图（节点=实体，边带 relation/source）
  ③ 遍历  从问题起点实体出发做限深多跳 BFS，收集路径三元组作为上下文 --LLM--> 答案

关系被归一化为「语义正向」，使正向遍历天然覆盖线性与聚合两类多跳：
  公司 --HAS_SUBSIDIARY--> 子公司
  公司 --HAS_CEO-->        高管
  高管 --GRADUATED_FROM--> 高校
  高校 --LOCATED_IN-->     城市
  投资方 --INVESTED_IN-->  公司

用法：
    python GraphRAG/graphrag_qa.py               # 进入循环问答模式（可输入 1/2 选择预备问题）
    python GraphRAG/graphrag_qa.py "你的问题"     # 直接回答单个自定义问题
    python GraphRAG/graphrag_qa.py --rebuild      # 忽略缓存重新抽取
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import networkx as nx  # noqa: E402

from common.chat import ChatClient  # noqa: E402
from common.config import ConfigError, load_config  # noqa: E402
from common.corpus import corpus_fingerprint, load_chunks  # noqa: E402
from common.questions import get_questions, run_interactive  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / ".cache"
MAX_HOPS = 4

# 固定关系集（语义正向方向）
RELATIONS = [
    "HAS_SUBSIDIARY",  # 母公司 -> 子公司
    "HAS_CEO",         # 公司   -> 高管(CEO)
    "GRADUATED_FROM",  # 人     -> 高校
    "LOCATED_IN",      # 高校/组织 -> 城市
    "INVESTED_IN",     # 投资方 -> 公司
]

EXTRACT_SYSTEM = (
    "你是一个信息抽取引擎。请从给定文本中抽取实体关系三元组，"
    "并严格输出 JSON。只允许使用如下固定关系（注意方向）：\n"
    "- HAS_SUBSIDIARY: 母公司 -> 子公司（例：星环科技 HAS_SUBSIDIARY 云枢智能）\n"
    "- HAS_CEO: 公司 -> 该公司的CEO（例：云枢智能 HAS_CEO 李明）\n"
    "- GRADUATED_FROM: 人 -> 毕业院校（例：李明 GRADUATED_FROM 未名理工大学）\n"
    "- LOCATED_IN: 机构/高校 -> 所在城市（例：未名理工大学 LOCATED_IN 江城）\n"
    "- INVESTED_IN: 投资方 -> 被投公司（例：磐石资本 INVESTED_IN 星环科技）\n"
    "输出格式：{\"triples\": [{\"subject\": \"...\", \"relation\": \"...\", "
    "\"object\": \"...\"}]}。"
    "实体名使用文本中的原始名称，不要翻译、不要添加解释。"
    "无法确定的关系不要输出。"
)


# ---------- 实体归一化 ----------
def normalize_entity(name: str) -> str:
    n = name.strip().strip("《》\"'“”").strip()
    return n


# ---------- ① 抽取 ----------
def extract_triples(chat: ChatClient, lang: str, rebuild: bool = False):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fp = corpus_fingerprint(lang)
    cache_path = CACHE_DIR / f"graph_{lang}_{fp}.json"
    if cache_path.exists() and not rebuild:
        print(f"[GraphRAG] 命中缓存，加载已抽取三元组：{cache_path.name}")
        return json.loads(cache_path.read_text(encoding="utf-8"))

    if chat is None:
        raise ConfigError(
            "首次抽取需要 chat API（用于实体关系抽取），请在 .env 配置 OPENAI_API_KEY。"
        )

    print("[GraphRAG] ① 抽取实体关系三元组（逐篇文档调用 LLM）…")
    chunks = load_chunks(lang)
    # 按来源文档聚合整篇文本，减少调用次数、提升上下文完整性
    by_doc: dict[str, list[str]] = {}
    for c in chunks:
        by_doc.setdefault(c.source, []).append(c.text)

    triples = []
    for source, paras in by_doc.items():
        doc_text = "\n\n".join(paras)
        raw = chat.complete(EXTRACT_SYSTEM, f"文本：\n{doc_text}")
        parsed = _parse_triples(raw)
        for t in parsed:
            rel = t.get("relation", "").strip().upper()
            if rel not in RELATIONS:
                continue
            subj = normalize_entity(t.get("subject", ""))
            obj = normalize_entity(t.get("object", ""))
            if not subj or not obj:
                continue
            triples.append(
                {"subject": subj, "relation": rel, "object": obj, "source": source}
            )
        print(f"    - {source}: 抽取 {len(parsed)} 条")

    cache_path.write_text(
        json.dumps(triples, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[GraphRAG] 抽取完成，共 {len(triples)} 条三元组，已缓存到 {cache_path.name}")
    return triples


def _parse_triples(raw: str):
    """从 LLM 输出中稳健解析 JSON 三元组。"""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        # 去掉可能的语言标注行
        if "\n" in raw:
            raw = raw.split("\n", 1)[1]
    # 截取第一个 { 到最后一个 }
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []
    return data.get("triples", []) if isinstance(data, dict) else []


# ---------- ② 建图 ----------
def build_graph(triples) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for t in triples:
        g.add_node(t["subject"])
        g.add_node(t["object"])
        g.add_edge(
            t["subject"], t["object"], relation=t["relation"], source=t["source"]
        )
    print(f"[GraphRAG] ② 构建知识图：{g.number_of_nodes()} 个节点，{g.number_of_edges()} 条边")
    return g


# ---------- ③ 多跳遍历 ----------
def find_start_entities(g: nx.MultiDiGraph, question: str, fallback):
    """从问题文本中匹配图内实体作为遍历起点。"""
    matches = [n for n in g.nodes if n in question]
    if matches:
        # 取最长匹配，避免误命中短名
        matches.sort(key=len, reverse=True)
        return [matches[0]]
    return [n for n in fallback if n in g.nodes]


def traverse(g: nx.MultiDiGraph, starts, max_hops: int = MAX_HOPS):
    """从起点做限深正向 BFS，收集路径上的三元组，并记录逐跳访问序列。"""
    collected = []  # 路径三元组
    seen_edges = set()
    visit_log = []  # (hop, subject, relation, object, source)
    visited_nodes = set(starts)
    queue = deque((s, 0) for s in starts)

    while queue:
        node, depth = queue.popleft()
        if depth >= max_hops:
            continue
        for _, nbr, data in g.out_edges(node, data=True):
            key = (node, data["relation"], nbr)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            triple = {
                "subject": node,
                "relation": data["relation"],
                "object": nbr,
                "source": data["source"],
            }
            collected.append(triple)
            visit_log.append((depth + 1, node, data["relation"], nbr, data["source"]))
            if nbr not in visited_nodes:
                visited_nodes.add(nbr)
                queue.append((nbr, depth + 1))
    return collected, visit_log


def print_traversal(starts, visit_log):
    print(f"[GraphRAG] ③ 从起点实体 {starts} 开始多跳遍历：")
    if not visit_log:
        print("    （未从起点走到任何边，请检查抽取结果或起点识别）")
        return
    for hop, subj, rel, obj, source in visit_log:
        print(f"    第{hop}跳: {subj} --{rel}--> {obj}   [来源: {source}]")


ANSWER_SYSTEM = (
    "你是一个严谨的问答助手。下面提供的是从知识图谱中沿实体关系多跳遍历得到的"
    "【事实三元组】。请仅依据这些事实进行推理并回答问题。"
    "如果需要，可以把多条三元组串联起来进行多跳推理。"
    "若事实不足以回答，请说明“根据现有资料无法确定”。"
)


def answer_from_path(chat, triples, question):
    lines = [
        f"{t['subject']} --{t['relation']}--> {t['object']}" for t in triples
    ]
    context = "\n".join(lines)
    if chat is None:
        print("\n[生成] 未配置 chat API，仅展示遍历路径（无法生成最终答案）。")
        return
    user = f"【事实三元组】\n{context}\n\n【问题】{question}"
    result = chat.complete(ANSWER_SYSTEM, user)
    print(f"\n[生成] 答案：\n{result}")


def answer(g, chat, question, fallback_starts):
    print("\n" + "=" * 70)
    print(f"[GraphRAG] 问题：{question}")
    print("-" * 70)
    starts = find_start_entities(g, question, fallback_starts)
    if not starts:
        print("[遍历] 未能在图中定位起点实体。")
        return
    triples, visit_log = traverse(g, starts)
    print_traversal(starts, visit_log)
    answer_from_path(chat, triples, question)


def main():
    rebuild = "--rebuild" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--rebuild"]

    try:
        cfg = load_config(require_chat=False)
    except ConfigError as e:
        print(f"配置错误：{e}")
        sys.exit(1)

    chat = ChatClient(cfg.chat) if cfg.chat.api_key else None
    if chat is None:
        print("[提示] 未配置 chat API Key；若无抽取缓存将无法建图。")

    triples = extract_triples(chat, cfg.corpus_lang, rebuild=rebuild)
    g = build_graph(triples)

    qs = get_questions(cfg.corpus_lang)
    # 自定义/自由问题时，起点回退用两题的所有起点实体
    fb = [e for q in qs.values() for e in q.start_entities]
    if args:
        answer(g, chat, " ".join(args), fb)
    else:
        run_interactive(cfg.corpus_lang, lambda q: answer(g, chat, q, fb))


if __name__ == "__main__":
    main()
