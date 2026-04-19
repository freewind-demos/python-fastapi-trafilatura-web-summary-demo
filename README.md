# Python FastAPI Trafilatura Web Summary Demo

## 简介

这个 Demo 演示如何把 `Trafilatura` 做成一个网页摘要工具。

Trafilatura 本身强项是网页正文提取，不是摘要器，所以这个 Demo 额外补了一个传统抽取式摘要算法。你打开页面后输入 URL，后端会先提正文，再选出最重要的几句。

## 快速开始

### 环境要求

- Python 3.11+

### 运行

```bash
cd /Users/peng.li/workspace/freewind-demos/python-fastapi-trafilatura-web-summary-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

浏览器打开 `http://127.0.0.1:8000`。

## 概念讲解

### 第一部分：Trafilatura 负责正文提取

核心代码在 [app.py](/Users/peng.li/workspace/freewind-demos/python-fastapi-trafilatura-web-summary-demo/app.py:1)：

```python
downloaded = trafilatura.fetch_url(str(payload.url))
text = trafilatura.extract(
    downloaded,
    output_format="txt",
    include_comments=False,
    include_tables=False,
    favor_recall=True,
)
```

这里做的事情是：

- 先抓取 URL
- 让 Trafilatura 把主要正文抽出来
- 顺便拿标题、作者、日期等元数据

Trafilatura 在 Python 生态里很适合拿来做预清洗，尤其适合“网页先转正文，再做后续处理”的流程。

### 第二部分：摘要逻辑是补充层

因为 Trafilatura 不是摘要器，所以 Demo 里补了一个简单传统摘要逻辑：

```python
frequencies = Counter(word for word in tokenize(text) if word not in STOPWORDS)
score = sum(frequencies[word] for word in words) / len(words) + coverage_bonus
```

它的思路是：

- 给正文切句
- 给词做词频统计
- 根据句子里重要词的密度给句子打分
- 选出得分最高的几句作为摘要

这不是生成式摘要，而是典型的抽取式摘要。

## 完整示例

前端静态页在 [templates/index.html](/Users/peng.li/workspace/freewind-demos/python-fastapi-trafilatura-web-summary-demo/templates/index.html:1) 和 [static/app.js](/Users/peng.li/workspace/freewind-demos/python-fastapi-trafilatura-web-summary-demo/static/app.js:1)。

前端把 URL 发给后端：

```js
const response = await fetch('/api/summarize', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ url }),
});
```

后端返回：

- 标题
- 作者
- 日期
- 摘要句
- 关键句
- 清洗后的全文

这样你既能看摘要，也能直接看 Trafilatura 最终抽出来的正文质量。

## 注意事项

- 这个 Demo 的重点是 `Trafilatura`，不是摘要算法本身
- 对极度依赖前端渲染的网站，Trafilatura 可能拿不到完整正文
- 某些网站会限制机器人访问

## 中文完整讲解

这个 demo 很适合用来理解一个现实问题：很多“网页摘要”任务，其实最难的不是摘要，而是先把网页里的正文找对。

如果正文都抽错了，后面的摘要算法再强也没意义。Trafilatura 正好适合做这一步。它会尽量把正文、标题、作者、日期这类信息从乱七八糟的网页结构里整理出来。

但 Trafilatura 自己不负责“把正文压成几句话”，所以这个 demo 又加了一层传统摘要逻辑。这样你就可以很直观地看到两层分工：

1. Trafilatura 负责去噪和正文提取
2. 传统算法负责从正文里挑核心句

如果你以后想做“先清洗网页，再送给大模型”的系统，这种结构非常常见，也非常实用。
