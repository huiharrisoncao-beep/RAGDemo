"""基于微软官方 GraphRAG 框架的问答程序（对照手写版 TEGraphRAG）。

与 RAG/ 和 TEGraphRAG/ 使用同一份语料（Docs/<lang>/）与同一批基准问题
（common/questions.py 的 Q1/Q2），以便三者横向对比。

与手写版的本质差异：官方框架是一条黑盒索引管线（分块 → 实体/关系抽取 →
Leiden 社区发现 → 社区报告 → 向量化 → parquet 产物），查询走 local / global
search，**没有可逐跳打印的遍历过程**。因此本程序默认只输出最终答案，另可
选打印一份索引产物摘要（实体/关系/社区数量）作为轻量“过程视图”。

模型后端：
  chat      复用现有 DeepSeek（common/config.py 的 OPENAI_* 配置）
  embedding 走本机 Ollama 的 OpenAI 兼容端点（默认 http://localhost:11434/v1，
            模型 embeddinggemma），使索引所需向量化离线、免费。

问题 → 检索模式：
  线性多跳（Q1）→ local search   聚合多跳（Q2）→ global search   自由问题 → local

用法：
    python MSGraphRAG/msgraphrag_qa.py                # 循环问答（1/2 选预备题）
    python MSGraphRAG/msgraphrag_qa.py "你的问题"      # 直接回答单个问题
    python MSGraphRAG/msgraphrag_qa.py --rebuild       # 忽略缓存重新索引
    python MSGraphRAG/msgraphrag_qa.py --summary       # 额外打印索引产物摘要
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import ConfigError, load_config  # noqa: E402
from common.corpus import corpus_fingerprint  # noqa: E402
from common.config import PROJECT_ROOT  # noqa: E402
from common.questions import get_questions, run_interactive  # noqa: E402

ROOT = Path(__file__).resolve().parent
COMMUNITY_LEVEL = 2
RESPONSE_TYPE = "Multiple Paragraphs"

# embedding 端点（本机 Ollama，OpenAI 兼容）；chat 复用 common/config 的 DeepSeek。
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
EMBED_MODEL = os.getenv("GRAPHRAG_EMBED_MODEL", "embeddinggemma")
EMBED_API_KEY = os.getenv("GRAPHRAG_EMBED_API_KEY", "ollama")


def _quiet_logs() -> None:
    os.environ.setdefault("LITELLM_LOG", "ERROR")
    for name in ("graphrag", "litellm", "httpx", "LiteLLM"):
        logging.getLogger(name).setLevel(logging.ERROR)


def _bypass_proxy_for_localhost() -> None:
    """让 litellm/httpx 直连本机 Ollama。

    macOS 的系统级 HTTP 代理会被 httpx（trust_env）用于本机地址，导致 embedding
    请求返回 502。把 Ollama 主机及 localhost 追加进 NO_PROXY/no_proxy 即可绕开。
    """
    from urllib.parse import urlparse

    host = urlparse(OLLAMA_BASE_URL).hostname or "localhost"
    extras = {host, "localhost", "127.0.0.1", "::1"}
    for var in ("NO_PROXY", "no_proxy"):
        current = {p.strip() for p in os.environ.get(var, "").split(",") if p.strip()}
        os.environ[var] = ",".join(sorted(current | extras))


# ---------- 兼容 DeepSeek：把 json_schema 结构化输出降级为 json_object ----------
def _patch_litellm_response_format() -> None:
    """DeepSeek 不支持 response_format=json_schema（会返回 400），但支持 json_object。

    官方社区报告等工作流会传入 pydantic 模型作为 response_format（litellm 据此发
    json_schema）。这里在进程内包装 litellm.(a)completion，遇到 pydantic/json_schema
    的 response_format 时统一降级为 {"type": "json_object"}；graphrag 随后仍用
    structure_completion_response(json.loads) 把返回文本解析回 pydantic，因此行为等价。
    对不含 response_format 的调用（如实体/关系抽取）无影响。
    """
    import litellm
    from pydantic import BaseModel

    if getattr(litellm, "_deepseek_json_object_patch", False):
        return

    def _downgrade(kwargs: dict) -> None:
        rf = kwargs.get("response_format")
        if rf is None:
            return
        is_pydantic = isinstance(rf, type) and issubclass(rf, BaseModel)
        is_json_schema = isinstance(rf, dict) and rf.get("type") == "json_schema"
        if is_pydantic or is_json_schema:
            kwargs["response_format"] = {"type": "json_object"}

    orig_completion = litellm.completion
    orig_acompletion = litellm.acompletion

    def completion(*args, **kwargs):
        _downgrade(kwargs)
        return orig_completion(*args, **kwargs)

    async def acompletion(*args, **kwargs):
        _downgrade(kwargs)
        return await orig_acompletion(*args, **kwargs)

    litellm.completion = completion
    litellm.acompletion = acompletion
    litellm._deepseek_json_object_patch = True


# ---------- 前置校验：Ollama embedding 端点可达 ----------
def preflight_embedding() -> int:
    """校验 embedding 端点可达，并返回其向量维度（用于配置向量库 vector_size）。"""
    url = f"{OLLAMA_BASE_URL}/embeddings"
    payload = json.dumps({"model": EMBED_MODEL, "input": "ping"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {EMBED_API_KEY}"},
    )
    # 绕过系统/环境代理直连本机 Ollama（macOS 下 urllib 会误用系统代理，导致 502）。
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        dim = len(data["data"][0]["embedding"])
        print(f"[MSGraphRAG] embedding 端点可用：{OLLAMA_BASE_URL} 模型 {EMBED_MODEL}（{dim} 维）")
        return dim
    except (urllib.error.URLError, KeyError, IndexError, ValueError) as e:
        raise ConfigError(
            f"无法访问 embedding 端点 {url}（模型 {EMBED_MODEL}）：{e}\n"
            f"请先启动 Ollama 并拉起该模型：ollama pull {EMBED_MODEL}\n"
            f"或用 OLLAMA_BASE_URL / GRAPHRAG_EMBED_MODEL 指定其他 OpenAI 兼容 embedding 端点。"
        ) from e


# ---------- 语料物化：Docs/<lang>/*.md -> ragtest/<lang>/input/*.txt ----------
def materialize_input(lang: str, root_dir: Path) -> int:
    docs_dir = PROJECT_ROOT / "Docs" / lang
    if not docs_dir.exists():
        raise FileNotFoundError(f"语料目录不存在：{docs_dir}")
    input_dir = root_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for old in input_dir.glob("*.txt"):
        old.unlink()
    count = 0
    for md in sorted(docs_dir.glob("*.md")):
        (input_dir / f"{md.stem}.txt").write_text(md.read_text(encoding="utf-8"), encoding="utf-8")
        count += 1
    if count == 0:
        raise ValueError(f"语料目录为空：{docs_dir}")
    return count


# ---------- 生成官方 settings.yaml ----------
def write_settings(root_dir: Path, chat_base_url: str, chat_model: str, vector_size: int) -> None:
    # 模型 ID 用官方默认名，各 workflow 的 *_model_id 默认即指向它们，无需逐一声明。
    settings = f"""\
completion_models:
  default_completion_model:
    model_provider: openai
    model: {chat_model}
    api_base: {chat_base_url}
    api_key: ${{GRAPHRAG_API_KEY}}
    retry:
      type: exponential_backoff

embedding_models:
  default_embedding_model:
    model_provider: openai
    model: {EMBED_MODEL}
    api_base: {OLLAMA_BASE_URL}
    api_key: ${{GRAPHRAG_EMBED_API_KEY}}
    retry:
      type: exponential_backoff

input:
  type: text

input_storage:
  type: file
  base_dir: "input"

output_storage:
  type: file
  base_dir: "output"

cache:
  type: json
  storage:
    type: file
    base_dir: "cache"

vector_store:
  type: lancedb
  db_uri: "output/lancedb"
  vector_size: {vector_size}

extract_claims:
  enabled: false
"""
    (root_dir / "settings.yaml").write_text(settings, encoding="utf-8")


# ---------- 索引（缓存复用） ----------
def ensure_index(lang: str, root_dir: Path, chat_cfg, vector_size: int, rebuild: bool) -> None:
    fp_file = root_dir / ".corpus_fingerprint"
    fp = corpus_fingerprint(lang)
    output_dir = root_dir / "output"
    up_to_date = (
        output_dir.exists()
        and (output_dir / "entities.parquet").exists()
        and fp_file.exists()
        and fp_file.read_text(encoding="utf-8").strip() == fp
    )
    if up_to_date and not rebuild:
        print(f"[MSGraphRAG] 命中索引缓存（指纹 {fp}），跳过索引。")
        return

    n = materialize_input(lang, root_dir)
    write_settings(root_dir, chat_cfg.base_url, chat_cfg.model, vector_size)
    print(f"[MSGraphRAG] 开始官方索引管线（{n} 篇文档，chat={chat_cfg.model}，embedding={EMBED_MODEL}）…")
    print("[MSGraphRAG] 该过程包含实体/关系抽取、社区发现与社区报告生成，需要多次 LLM 调用，请耐心等待。")

    from graphrag.api import build_index
    from graphrag.config.load_config import load_config as gr_load_config

    gr_config = gr_load_config(root_dir=root_dir)
    results = asyncio.run(build_index(config=gr_config))
    errors = [r for r in results if getattr(r, "error", None)]
    if errors:
        for r in errors:
            print(f"[MSGraphRAG] 工作流 {r.workflow} 失败：{r.error}")
        raise RuntimeError("索引管线存在失败的工作流，详见上方日志。")
    fp_file.write_text(fp, encoding="utf-8")
    print("[MSGraphRAG] 索引完成，产物已写入 output/。")


# ---------- 读取索引产物 ----------
def _load_outputs(gr_config, names, optional=None):
    import pandas as pd  # noqa: F401

    from graphrag_storage import create_storage
    from graphrag_storage.tables.table_provider_factory import create_table_provider
    from graphrag.data_model.data_reader import DataReader

    storage_obj = create_storage(gr_config.output_storage)
    table_provider = create_table_provider(gr_config.table_provider, storage=storage_obj)
    reader = DataReader(table_provider)
    out = {name: asyncio.run(getattr(reader, name)()) for name in names}
    for name in optional or []:
        out[name] = (
            asyncio.run(getattr(reader, name)())
            if asyncio.run(table_provider.has(name))
            else None
        )
    return out


def print_summary(gr_config) -> None:
    dfs = _load_outputs(gr_config, ["entities", "relationships", "communities", "community_reports"])
    print(
        "[MSGraphRAG] 索引产物摘要："
        f"实体 {len(dfs['entities'])} | 关系 {len(dfs['relationships'])} | "
        f"社区 {len(dfs['communities'])} | 社区报告 {len(dfs['community_reports'])}"
    )


# ---------- 问题 → 检索模式路由 ----------
def route(question: str, lang: str) -> str:
    """线性多跳(Q1)→local，聚合多跳(Q2)→global，自由问题默认 local。"""
    for q in get_questions(lang).values():
        if q.text.strip() == question.strip():
            return "global" if q.kind == "aggregate" else "local"
    return "local"


# ---------- 查询 ----------
def answer(gr_config, question: str, lang: str) -> None:
    mode = route(question, lang)
    print("\n" + "=" * 70)
    print(f"[MSGraphRAG] 问题：{question}")
    print(f"[MSGraphRAG] 检索模式：{mode} search")
    print("-" * 70)

    from graphrag.api import global_search, local_search

    if mode == "global":
        dfs = _load_outputs(gr_config, ["entities", "communities", "community_reports"])
        response, _ = asyncio.run(
            global_search(
                config=gr_config,
                entities=dfs["entities"],
                communities=dfs["communities"],
                community_reports=dfs["community_reports"],
                community_level=COMMUNITY_LEVEL,
                dynamic_community_selection=False,
                response_type=RESPONSE_TYPE,
                query=question,
            )
        )
    else:
        dfs = _load_outputs(
            gr_config,
            ["entities", "communities", "community_reports", "text_units", "relationships"],
            optional=["covariates"],
        )
        response, _ = asyncio.run(
            local_search(
                config=gr_config,
                entities=dfs["entities"],
                communities=dfs["communities"],
                community_reports=dfs["community_reports"],
                text_units=dfs["text_units"],
                relationships=dfs["relationships"],
                covariates=dfs["covariates"],
                community_level=COMMUNITY_LEVEL,
                response_type=RESPONSE_TYPE,
                query=question,
            )
        )
    print(f"\n[生成] 答案：\n{response}")


def main() -> None:
    _quiet_logs()
    _bypass_proxy_for_localhost()
    _patch_litellm_response_format()
    rebuild = "--rebuild" in sys.argv
    summary = "--summary" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--rebuild", "--summary")]

    try:
        cfg = load_config(require_chat=True)
    except ConfigError as e:
        print(f"配置错误：{e}")
        sys.exit(1)

    # 供官方 settings.yaml 的 ${...} 占位符在进程内解析，避免把密钥写入磁盘。
    os.environ["GRAPHRAG_API_KEY"] = cfg.chat.api_key
    os.environ["GRAPHRAG_EMBED_API_KEY"] = EMBED_API_KEY

    try:
        embed_dim = preflight_embedding()
    except ConfigError as e:
        print(f"配置错误：{e}")
        sys.exit(1)

    lang = cfg.corpus_lang
    root_dir = ROOT / "ragtest" / lang
    root_dir.mkdir(parents=True, exist_ok=True)

    try:
        ensure_index(lang, root_dir, cfg.chat, embed_dim, rebuild=rebuild)
    except Exception as e:  # noqa: BLE001 - 索引失败给出可诊断提示后退出
        print(f"[MSGraphRAG] 索引失败：{e}")
        sys.exit(1)

    from graphrag.config.load_config import load_config as gr_load_config

    gr_config = gr_load_config(root_dir=root_dir)
    if summary:
        print_summary(gr_config)

    if args:
        answer(gr_config, " ".join(args), lang)
    else:
        run_interactive(lang, lambda q: answer(gr_config, q, lang))


if __name__ == "__main__":
    main()
