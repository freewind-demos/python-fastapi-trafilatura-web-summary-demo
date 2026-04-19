from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

import trafilatura
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, HttpUrl


app = FastAPI(title="Trafilatura Web Summary Demo")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


class SummaryRequest(BaseModel):
    url: HttpUrl
    maxSummaryLength: int = Field(default=0)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "tool_name": "Trafilatura",
            "subtitle": "正文提取主力用 Trafilatura，摘要用自带的传统句子打分补齐。",
        },
    )


@app.post("/api/summarize")
async def summarize(payload: SummaryRequest) -> dict[str, Any]:
    downloaded = trafilatura.fetch_url(str(payload.url))
    if not downloaded:
        raise HTTPException(status_code=422, detail="Trafilatura 没有抓到网页内容。")

    metadata = trafilatura.extract_metadata(downloaded)
    text = trafilatura.extract(
        downloaded,
        output_format="txt",
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )

    if not text or len(text.strip()) < 180:
        raise HTTPException(
            status_code=422,
            detail="Trafilatura 没有提取出足够正文。这个页面可能不是文章页，或者结构比较特殊。",
        )

    clean_text = compact_whitespace(text)
    metadata_object = {
        "title": metadata.title if metadata and metadata.title else "",
        "author": metadata.author if metadata and metadata.author else "",
        "date": metadata.date if metadata and metadata.date else "",
        "description": metadata.description if metadata and metadata.description else "",
        "url": str(payload.url),
    }
    extracted_object = {
        "metadata": metadata_object,
        "text": clean_text,
    }
    summary = limit_summary_length(summarize_text(clean_text, 4), payload.maxSummaryLength)
    highlights = build_highlights(clean_text, 3)

    return {
        "tool": "Trafilatura",
        "title": metadata.title if metadata and metadata.title else fallback_title(str(payload.url)),
        "author": metadata.author if metadata and metadata.author else "",
        "hostname": urlparse(str(payload.url)).hostname or "",
        "date": metadata.date if metadata and metadata.date else "",
        "description": metadata.description if metadata and metadata.description else "",
        "rawText": downloaded,
        "cleanedText": json_dump(extracted_object),
        "summary": summary,
        "highlights": highlights,
        "text": clean_text,
        "pipeline": [
            {
                "step": "1. 原始抓取",
                "core": "trafilatura.fetch_url",
                "helper": "项目内置 HTML 粗转文本",
                "detail": "先把原始 HTML 抓回来，再做一次非常粗糙的文本化，仅用于对比网页噪音有多少。",
                "output": "产出：整页粗文本，噪音比较多，主要拿来对比。",
                "focus": False,
            },
            {
                "step": "2. 去噪 / 正文提取",
                "core": "Trafilatura",
                "helper": "extract_metadata 提供标题作者日期",
                "detail": "这个 demo 的核心能力在这一步。Trafilatura 负责识别文章主内容，把导航和页脚尽量剥掉。",
                "output": "产出：清洗后的正文文本，这是当前 demo 的重点展示结果。",
                "focus": True,
            },
            {
                "step": "3. 摘要",
                "core": "项目内置词频句子打分",
                "helper": "无第三方摘要库",
                "detail": "Trafilatura 不是摘要器，所以这里补了一个传统抽取式摘要算法，专门把正文压成几句。",
                "output": "产出：从正文挑出的几句摘要。",
                "focus": False,
            },
        ],
        "stats": {
            "characters": len(clean_text),
            "sentences": len(split_sentences(clean_text)),
            "summary_sentences": len(summary),
        },
        "sizes": {
            "rawText": measure_text(downloaded),
            "cleanedText": measure_text(json_dump(extracted_object)),
            "summaryText": measure_text("\n\n".join(summary)),
        },
    }


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def measure_text(text: str) -> dict[str, int]:
    return {
        "characters": len(text),
        "bytes": len(text.encode("utf-8")),
    }


def limit_summary_length(summary: list[str], max_length: int) -> list[str]:
    joined = "\n\n".join(summary).strip()
    if max_length <= 0:
        return summary
    if len(joined) <= max_length:
        return summary
    return [joined[:max_length].strip()]


def json_dump(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False, indent=2)


def split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[。！？.!?])\s+", text)
        if len(sentence.strip()) > 20
    ]


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", text.lower())


def summarize_text(text: str, sentence_count: int) -> list[str]:
    sentences = split_sentences(text)
    if len(sentences) <= sentence_count:
        return sentences

    frequencies = Counter(word for word in tokenize(text) if word not in STOPWORDS)
    scored: list[tuple[int, float, str]] = []

    for index, sentence in enumerate(sentences):
        words = [word for word in tokenize(sentence) if word not in STOPWORDS]
        if not words:
            continue
        coverage_bonus = min(len(set(words)), 12) / 12
        score = sum(frequencies[word] for word in words) / len(words) + coverage_bonus
        scored.append((index, score, sentence))

    best = sorted(scored, key=lambda item: item[1], reverse=True)[:sentence_count]
    return [item[2] for item in sorted(best, key=lambda item: item[0])]


def build_highlights(text: str, limit: int) -> list[str]:
    paragraphs = [chunk.strip() for chunk in text.split("\n") if len(chunk.strip()) > 30]
    if paragraphs:
        return paragraphs[:limit]
    return split_sentences(text)[:limit]


def fallback_title(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or "Untitled page"


STOPWORDS = {
    "the",
    "and",
    "that",
    "this",
    "with",
    "from",
    "have",
    "will",
    "their",
    "about",
    "there",
    "into",
    "would",
    "could",
    "should",
    "一个",
    "一种",
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
    "以及",
    "但是",
    "如果",
    "因为",
    "所以",
    "进行",
    "已经",
    "可以",
    "没有",
}
