"""Build a tiny static blog from Markdown files in posts/."""

from __future__ import annotations

import html
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
STATIC_DIR = ROOT / "static"
SITE_DIR = ROOT / "site"
CONFIG_PATH = ROOT / "config.toml"


@dataclass
class SiteConfig:
    name: str
    tagline: str
    home_heading: str
    home_lead: str
    posts_lead: str
    tags_lead: str
    footer: str
    home_label: str
    posts_label: str
    tags_label: str


def load_config() -> SiteConfig:
    with CONFIG_PATH.open("rb") as f:
        data = tomllib.load(f)
    site = data.get("site", {})
    nav = data.get("nav", {})
    return SiteConfig(
        name=site.get("name", "initial_trial-blog"),
        tagline=site.get("tagline", ""),
        home_heading=site.get("home_heading", "首页"),
        home_lead=site.get("home_lead", ""),
        posts_lead=site.get("posts_lead", ""),
        tags_lead=site.get("tags_lead", ""),
        footer=site.get("footer", ""),
        home_label=nav.get("home_label", "首页"),
        posts_label=nav.get("posts_label", "文章/日志"),
        tags_label=nav.get("tags_label", "标签"),
    )


@dataclass
class Post:
    slug: str
    title: str
    date_raw: str
    date_display: str
    date_sort: str
    summary: str
    tags: list[str] = field(default_factory=list)
    body_md: str = ""
    source_name: str = ""
    ai_takeaway: str = ""
    ai_points: list[str] = field(default_factory=list)
    ai_next: str = ""


def slugify(stem: str) -> str:
    slug = stem.strip().lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^\w\u4e00-\u9fff\-]+", "-", slug, flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "post"


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, parts[2].lstrip("\n")


def parse_tags(raw: str) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[,，]", raw) if part.strip()]


def parse_points(raw: str) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in re.split(r"[;；|｜]", raw) if part.strip()]


def format_datetime(raw: str) -> tuple[str, str]:
    """Return (display_text, sort_key)."""
    text = (raw or "").strip()
    if not text:
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M"), now.isoformat(timespec="minutes")

    candidates = [
        text,
        text.replace("Z", "+00:00"),
        text.replace("T", " ").replace("Z", ""),
    ]
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    )

    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            return dt.strftime("%Y-%m-%d %H:%M"), dt.isoformat(timespec="minutes")
        except ValueError:
            pass
        for fmt in formats:
            try:
                dt = datetime.strptime(candidate, fmt)
                if fmt in ("%Y-%m-%d", "%Y/%m/%d"):
                    return dt.strftime("%Y-%m-%d"), dt.isoformat(timespec="minutes")
                return dt.strftime("%Y-%m-%d %H:%M"), dt.isoformat(timespec="minutes")
            except ValueError:
                continue

    return text, text


def md_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = re.sub(
        r"\[(.+?)\]\((.+?)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    return text


def markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("### "):
            out.append(f"<h3>{md_inline(stripped[4:])}</h3>")
            i += 1
            continue
        if stripped.startswith("## "):
            out.append(f"<h2>{md_inline(stripped[3:])}</h2>")
            i += 1
            continue
        if stripped.startswith("# "):
            out.append(f"<h1>{md_inline(stripped[2:])}</h1>")
            i += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                header = rows[0]
                body_rows = rows[1:]
                thead = "<tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in header) + "</tr>"
                tbody = "".join(
                    "<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in row) + "</tr>"
                    for row in body_rows
                )
                out.append(f'<table class="md-table"><thead>{thead}</thead><tbody>{tbody}</tbody></table>')
            continue

        if stripped.startswith("- "):
            items: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{md_inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                items.append(f"<li>{md_inline(item_text)}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        para = [stripped]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].strip().startswith("#")
            and not lines[i].strip().startswith("- ")
            and not lines[i].strip().startswith("|")
            and not re.match(r"^\d+\.\s+", lines[i].strip())
        ):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{md_inline(' '.join(para))}</p>")

    return "\n".join(out)


def render_tags(tags: list[str], root_prefix: str = "") -> str:
    if not tags:
        return ""
    chips = []
    for tag in tags:
        href = f"{root_prefix}tags/{slugify(tag)}.html"
        chips.append(
            f'<a class="tag" href="{html.escape(href)}">{html.escape(tag)}</a>'
        )
    return f'<div class="tags">{"".join(chips)}</div>'


def group_posts_by_tag(posts: list[Post]) -> dict[str, list[Post]]:
    grouped: dict[str, list[Post]] = {}
    for post in posts:
        for tag in post.tags:
            grouped.setdefault(tag, []).append(post)
    return dict(sorted(grouped.items(), key=lambda item: item[0]))


def render_ai_brief(post: Post) -> str:
    if not (post.ai_takeaway or post.ai_points or post.ai_next):
        return ""

    rows: list[str] = []
    if post.ai_takeaway:
        rows.append(
            "<tr><th scope=\"row\">一句话</th>"
            f"<td>{html.escape(post.ai_takeaway)}</td></tr>"
        )
    if post.ai_points:
        items = "".join(f"<li>{html.escape(p)}</li>" for p in post.ai_points)
        rows.append(
            f'<tr><th scope="row">要点</th><td><ul class="ai-points">{items}</ul></td></tr>'
        )
    if post.ai_next:
        rows.append(
            "<tr><th scope=\"row\">下一步</th>"
            f"<td>{html.escape(post.ai_next)}</td></tr>"
        )

    return f"""
<section class="ai-brief" aria-label="AI 提炼">
  <div class="ai-brief-head">
    <p class="ai-label">AI 提炼</p>
    <p class="ai-sub">结构化摘要 · 便于回顾</p>
  </div>
  <table class="ai-table">
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</section>
"""


def load_posts() -> list[Post]:
    posts: list[Post] = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(raw)
        title = meta.get("title") or path.stem
        date_display, date_sort = format_datetime(meta.get("date", ""))
        summary = meta.get("summary") or ""
        tags = parse_tags(meta.get("tags", ""))
        posts.append(
            Post(
                slug=slugify(path.stem),
                title=title,
                date_raw=meta.get("date", ""),
                date_display=date_display,
                date_sort=date_sort,
                summary=summary,
                tags=tags,
                body_md=body,
                source_name=path.name,
                ai_takeaway=meta.get("ai_takeaway", ""),
                ai_points=parse_points(meta.get("ai_points", "")),
                ai_next=meta.get("ai_next", ""),
            )
        )
    posts.sort(key=lambda p: p.date_sort, reverse=True)
    return posts


def page_shell(
    cfg: SiteConfig,
    title: str,
    active: str,
    content: str,
    root_prefix: str = "",
) -> str:
    home_href = f"{root_prefix}index.html"
    posts_href = f"{root_prefix}posts.html"
    tags_href = f"{root_prefix}tags.html"
    css_href = f"{root_prefix}css/style.css"

    home_class = "active" if active == "home" else ""
    posts_class = "active" if active == "posts" else ""
    tags_class = "active" if active == "tags" else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · {html.escape(cfg.name)}</title>
  <link rel="stylesheet" href="{css_href}">
</head>
<body>
  <div class="layout">
    <main class="main">
      {content}
      <p class="footer-note">{html.escape(cfg.footer)}</p>
    </main>
    <aside class="sidebar">
      <a class="brand" href="{home_href}">
        {html.escape(cfg.name)}
        <span>{html.escape(cfg.tagline)}</span>
      </a>
      <nav class="nav">
        <a class="{home_class}" href="{home_href}">{html.escape(cfg.home_label)}</a>
        <a class="{posts_class}" href="{posts_href}">{html.escape(cfg.posts_label)}</a>
        <a class="{tags_class}" href="{tags_href}">{html.escape(cfg.tags_label)}</a>
      </nav>
    </aside>
  </div>
</body>
</html>
"""


def render_post_card(post: Post, article_href: str, root_prefix: str = "") -> str:
    summary = html.escape(post.summary) if post.summary else "（暂无摘要）"
    tags = render_tags(post.tags, root_prefix=root_prefix)
    return f"""<li>
  <a class="title" href="{html.escape(article_href)}">{html.escape(post.title)}</a>
  <div class="meta">发布时间 {html.escape(post.date_display)}</div>
  {tags}
  <p class="summary">{summary}</p>
</li>"""


def render_home(cfg: SiteConfig, posts: list[Post]) -> str:
    recent = posts[:3]
    items = [
        render_post_card(post, f"articles/{post.slug}.html", root_prefix="")
        for post in recent
    ]
    recent_html = (
        '<ul class="post-list">' + "".join(items) + "</ul>"
        if items
        else "<p>还没有文章。用本机编辑器新建一篇吧。</p>"
    )

    content = f"""
<p class="eyebrow">Home</p>
<h1>{html.escape(cfg.home_heading)}</h1>
<p class="lead">{html.escape(cfg.home_lead)}</p>
<h2>最近文章</h2>
{recent_html}
<p><a href="posts.html">查看全部文章 →</a></p>
"""
    return page_shell(cfg, cfg.home_label, "home", content)


def render_posts_index(cfg: SiteConfig, posts: list[Post]) -> str:
    cards = []
    for post in posts:
        summary = html.escape(post.summary) if post.summary else "（暂无摘要）"
        cards.append(
            f"""<li>
  <a class="title" href="articles/{html.escape(post.slug)}.html">{html.escape(post.title)}</a>
  <div class="meta">发布时间 {html.escape(post.date_display)} · 来源 {html.escape(post.source_name)}</div>
  {render_tags(post.tags)}
  <p class="summary">{summary}</p>
</li>"""
        )

    list_html = (
        '<ul class="post-list">' + "".join(cards) + "</ul>"
        if cards
        else "<p>暂时没有文章。</p>"
    )

    content = f"""
<p class="eyebrow">Articles</p>
<h1>{html.escape(cfg.posts_label)}</h1>
<p class="lead">{html.escape(cfg.posts_lead)}</p>
{list_html}
<section class="panel">
  <h2>在网页里写文章（推荐）</h2>
  <ol>
    <li>在项目目录运行：<code>python admin_server.py</code></li>
    <li>浏览器打开 <code>http://127.0.0.1:8766/</code></li>
    <li>点「新建文章」或「编辑」，保存后会自动构建</li>
  </ol>
  <p>这是<strong>本机编辑器</strong>：方便日常写作，但不会出现在公网部署里（公网站点保持只读，更安全）。</p>
</section>
"""
    return page_shell(cfg, cfg.posts_label, "posts", content)


def render_tags_index(cfg: SiteConfig, posts: list[Post]) -> str:
    grouped = group_posts_by_tag(posts)
    if not grouped:
        list_html = "<p>还没有标签。在文章文头加上 <code>tags: Vibe入门</code> 即可。</p>"
    else:
        items = []
        for tag, tagged_posts in grouped.items():
            items.append(
                f"""<li>
  <a class="title" href="tags/{html.escape(slugify(tag))}.html">{html.escape(tag)}</a>
  <div class="meta">{len(tagged_posts)} 篇</div>
</li>"""
            )
        list_html = '<ul class="post-list">' + "".join(items) + "</ul>"

    content = f"""
<p class="eyebrow">Tags</p>
<h1>{html.escape(cfg.tags_label)}</h1>
<p class="lead">{html.escape(cfg.tags_lead)}</p>
{list_html}
"""
    return page_shell(cfg, cfg.tags_label, "tags", content)


def render_tag_page(cfg: SiteConfig, tag: str, posts: list[Post]) -> str:
    cards = [
        render_post_card(post, f"../articles/{post.slug}.html", root_prefix="../")
        for post in posts
    ]
    list_html = (
        '<ul class="post-list">' + "".join(cards) + "</ul>"
        if cards
        else "<p>该标签下暂无文章。</p>"
    )
    content = f"""
<p class="eyebrow">Tag</p>
<h1>{html.escape(tag)}</h1>
<p class="lead">标签归档 · {len(posts)} 篇</p>
{list_html}
<p><a href="../tags.html">← 全部标签</a></p>
"""
    return page_shell(cfg, tag, "tags", content, root_prefix="../")


def render_article(cfg: SiteConfig, post: Post) -> str:
    body = markdown_to_html(post.body_md)
    ai_brief = render_ai_brief(post)
    content = f"""
<p class="eyebrow">Article</p>
<h1>{html.escape(post.title)}</h1>
<p class="meta">发布时间 {html.escape(post.date_display)} · 源文件 <code>{html.escape(post.source_name)}</code></p>
{render_tags(post.tags, root_prefix="../")}
<article class="prose">
{body}
</article>
{ai_brief}
<p><a href="../posts.html">← 返回文章列表</a></p>
"""
    return page_shell(cfg, post.title, "posts", content, root_prefix="../")


def build() -> None:
    cfg = load_config()

    if not POSTS_DIR.exists():
        POSTS_DIR.mkdir(parents=True)

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)
    (SITE_DIR / "articles").mkdir()
    (SITE_DIR / "tags").mkdir()

    shutil.copytree(STATIC_DIR / "css", SITE_DIR / "css")

    posts = load_posts()
    (SITE_DIR / "index.html").write_text(render_home(cfg, posts), encoding="utf-8")
    (SITE_DIR / "posts.html").write_text(render_posts_index(cfg, posts), encoding="utf-8")
    (SITE_DIR / "tags.html").write_text(render_tags_index(cfg, posts), encoding="utf-8")

    for post in posts:
        out = SITE_DIR / "articles" / f"{post.slug}.html"
        out.write_text(render_article(cfg, post), encoding="utf-8")

    for tag, tagged in group_posts_by_tag(posts).items():
        out = SITE_DIR / "tags" / f"{slugify(tag)}.html"
        out.write_text(render_tag_page(cfg, tag, tagged), encoding="utf-8")

    print(f"Built {len(posts)} post(s) into {SITE_DIR}")


if __name__ == "__main__":
    build()
