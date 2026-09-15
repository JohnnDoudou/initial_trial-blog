"""Local-only web editor for creating/editing Markdown posts.

Bind to 127.0.0.1 only. Not for public internet deployment.
Run: python admin_server.py
Open: http://127.0.0.1:8766/
"""

from __future__ import annotations

import html
import re
import subprocess
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
HOST = "127.0.0.1"
PORT = 8766


def slugify(text: str) -> str:
    slug = text.strip().lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^\w\u4e00-\u9fff\-]+", "-", slug, flags=re.UNICODE)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "post"


def safe_post_name(name: str) -> str | None:
    name = Path(name).name
    if not name.endswith(".md"):
        return None
    if ".." in name or "/" in name or "\\" in name:
        return None
    return name


def list_posts() -> list[Path]:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(POSTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


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


def build_markdown(fields: dict[str, str]) -> str:
    lines = [
        "---",
        f"title: {fields.get('title', '').strip() or '未命名文章'}",
        f"date: {fields.get('date', '').strip() or datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"tags: {fields.get('tags', '').strip() or 'Vibe入门'}",
        f"summary: {fields.get('summary', '').strip()}",
        f"ai_takeaway: {fields.get('ai_takeaway', '').strip()}",
        f"ai_points: {fields.get('ai_points', '').strip()}",
        f"ai_next: {fields.get('ai_next', '').strip()}",
        "---",
        "",
        fields.get("body", "").replace("\r\n", "\n").strip(),
        "",
    ]
    return "\n".join(lines)


def suggested_filename(title: str, date_str: str) -> str:
    date_part = (date_str or "")[:10]
    if not re.match(r"\d{4}-\d{2}-\d{2}", date_part):
        date_part = datetime.now().strftime("%Y-%m-%d")
    return f"{date_part}-{slugify(title)}.md"


def run_build() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / "build.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()
    except OSError as exc:
        return False, str(exc)


def page(title: str, body: str) -> bytes:
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Cache-Control" content="no-store">
  <title>{html.escape(title)} · 本机编辑器</title>
  <style>
    :root {{
      --bg: #f3efe6; --paper: #fffaf2; --ink: #1c2430; --muted: #5c6675;
      --line: #d7d0c3; --accent: #0f6a5a; --soft: #d8efe9;
      --font: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: var(--font); color: var(--ink);
      background: linear-gradient(180deg, #efe8db, var(--bg));
      line-height: 1.6;
    }}
    .wrap {{ max-width: 880px; margin: 0 auto; padding: 1.5rem 1rem 3rem; }}
    .card {{
      background: var(--paper); border: 1px solid var(--line);
      border-radius: 16px; padding: 1.25rem 1.4rem; box-shadow: 0 12px 40px rgba(28,36,48,.08);
    }}
    h1 {{ margin: 0 0 .6rem; font-size: 1.6rem; }}
    .muted {{ color: var(--muted); }}
    .nav {{ display: flex; flex-wrap: wrap; gap: .6rem; margin: 1rem 0 1.2rem; }}
    a.btn, button, button.btn {{
      display: inline-block; border: 0; border-radius: 10px; padding: .55rem .9rem;
      background: var(--accent); color: #fff; text-decoration: none; cursor: pointer; font: inherit;
    }}
    a.btn.secondary, button.secondary, button.btn.secondary {{ background: #1f2a36; }}
    a.btn.ghost {{ background: transparent; color: var(--accent); border: 1px solid #b7ddd4; }}
    .list {{ list-style: none; padding: 0; margin: 0; }}
    .list li {{
      padding: .85rem 0; border-bottom: 1px solid var(--line);
      display: flex; justify-content: space-between; gap: 1rem; align-items: baseline;
    }}
    label {{ display: block; margin: .85rem 0 .3rem; font-weight: 600; font-size: .92rem; }}
    input, textarea {{
      width: 100%; border: 1px solid var(--line); border-radius: 10px;
      padding: .65rem .75rem; font: inherit; background: #fff;
    }}
    textarea {{ min-height: 280px; resize: vertical; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: .8rem; }}
    .note {{ margin-top: 1rem; padding: .9rem 1rem; background: var(--soft); border-radius: 12px; border: 1px solid #b7ddd4; }}
    .ok {{ color: #0a4f43; }}
    .err {{ color: #8a1f1f; }}
    @media (max-width: 700px) {{ .row {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      {body}
    </div>
  </div>
</body>
</html>
"""
    return doc.encode("utf-8")


def render_home(message: str = "", ok: bool | None = None) -> bytes:
    items = []
    for path in list_posts():
        meta, _ = parse_front_matter(path.read_text(encoding="utf-8"))
        title = meta.get("title") or path.stem
        href = f"/edit?file={quote(path.name)}"
        items.append(
            f'<li><div><strong>{html.escape(title)}</strong>'
            f'<div class="muted">{html.escape(path.name)}</div></div>'
            f'<a class="btn ghost" href="{href}">编辑</a></li>'
        )
    msg_html = ""
    if message:
        cls = "ok" if ok else "err"
        msg_html = f'<p class="{cls}">{html.escape(message)}</p>'

    body = f"""
<h1>本机文章编辑器</h1>
<p class="muted">只监听本机 127.0.0.1，不会暴露到公网。保存后会自动运行 build.py。</p>
{msg_html}
<nav class="nav">
  <a class="btn" href="/new">新建文章</a>
  <a class="btn secondary" href="/preview/" target="_blank">预览站点</a>
</nav>
<ul class="list">
  {''.join(items) if items else '<li class="muted">还没有文章</li>'}
</ul>
<div class="note">
  公网静态站仍然只读。以后要「外网也能写」，需要登录与服务器，那是另一阶段。
</div>
"""
    return page("本机编辑器", body)


def render_form(
    *,
    heading: str,
    action: str,
    fields: dict[str, str],
    filename: str = "",
    filename_locked: bool = False,
) -> bytes:
    locked = "readonly" if filename_locked else ""
    body = f"""
<h1>{html.escape(heading)}</h1>
<p class="muted"><a href="/">← 返回列表</a></p>
<form method="post" action="{html.escape(action)}" id="post-form">
  <input type="hidden" name="original_file" value="{html.escape(filename)}">
  <label>文件名（.md）</label>
  <input name="filename" value="{html.escape(filename)}" {locked} required>
  <div class="row">
    <div>
      <label>标题</label>
      <input name="title" value="{html.escape(fields.get('title', ''))}" required>
    </div>
    <div>
      <label>发布时间</label>
      <input name="date" value="{html.escape(fields.get('date', datetime.now().strftime('%Y-%m-%d %H:%M')))}" required>
    </div>
  </div>
  <div class="row">
    <div>
      <label>标签（逗号分隔）</label>
      <input name="tags" value="{html.escape(fields.get('tags', 'Vibe入门'))}">
    </div>
    <div>
      <label>摘要</label>
      <input name="summary" value="{html.escape(fields.get('summary', ''))}" placeholder="列表页显示的一句话">
    </div>
  </div>
  <label>正文（Markdown）</label>
  <textarea name="body">{html.escape(fields.get('body', ''))}</textarea>
  <p class="muted">摘要与文末「AI 提炼」可留空，或写完后在 Cursor 里让助手根据全文填写。不要用本地脚本自动拼。</p>
  <label>AI 提炼 · 一句话</label>
  <input name="ai_takeaway" value="{html.escape(fields.get('ai_takeaway', ''))}">
  <label>AI 提炼 · 要点（用分号分隔）</label>
  <input name="ai_points" value="{html.escape(fields.get('ai_points', ''))}" placeholder="要点1; 要点2; 要点3">
  <label>AI 提炼 · 下一步</label>
  <input name="ai_next" value="{html.escape(fields.get('ai_next', ''))}">
  <nav class="nav" style="margin-top:1rem">
    <button type="submit">保存并构建</button>
    <a class="btn ghost" href="/">取消</a>
  </nav>
</form>
"""
    return page(heading, body)


class AdminHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def send_html(self, payload: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self) -> None:
        try:
            self._do_GET()
        except Exception as exc:
            sys.stderr.write("GET error: %s\n" % exc)
            try:
                self.send_html(
                    page("错误", f"<p class='err'>服务器处理出错：{html.escape(str(exc))}</p><p><a href='/'>返回</a></p>"),
                    500,
                )
            except Exception:
                pass

    def _do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index"):
            self.send_html(render_home())
            return

        if path == "/new":
            self.send_html(
                render_form(
                    heading="新建文章",
                    action="/save",
                    fields={"body": "# 标题\n\n在这里写正文。\n"},
                    filename=suggested_filename("new-post", datetime.now().strftime("%Y-%m-%d")),
                )
            )
            return

        if path == "/edit":
            qs = parse_qs(parsed.query)
            name = safe_post_name(unquote(qs.get("file", [""])[0]))
            if not name:
                self.send_html(page("错误", "<p class='err'>无效文件名</p><p><a href='/'>返回</a></p>"), 400)
                return
            target = POSTS_DIR / name
            if not target.exists():
                self.send_html(page("错误", "<p class='err'>找不到文章</p><p><a href='/'>返回</a></p>"), 404)
                return
            meta, body_md = parse_front_matter(target.read_text(encoding="utf-8"))
            fields = {
                "title": meta.get("title", ""),
                "date": meta.get("date", ""),
                "tags": meta.get("tags", ""),
                "summary": meta.get("summary", ""),
                "ai_takeaway": meta.get("ai_takeaway", ""),
                "ai_points": meta.get("ai_points", ""),
                "ai_next": meta.get("ai_next", ""),
                "body": body_md,
            }
            self.send_html(
                render_form(
                    heading=f"编辑：{meta.get('title', name)}",
                    action="/save",
                    fields=fields,
                    filename=name,
                    filename_locked=True,
                )
            )
            return

        if path.startswith("/preview"):
            self.serve_preview(path)
            return

        self.send_html(page("404", "<p>页面不存在</p><p><a href='/'>返回</a></p>"), 404)

    def serve_preview(self, path: str) -> None:
        rel = path[len("/preview") :].lstrip("/")
        if rel == "" or rel.endswith("/"):
            rel = (rel + "index.html") if rel else "index.html"
        # prevent path escape
        candidate = (ROOT / "site" / rel).resolve()
        site_root = (ROOT / "site").resolve()
        try:
            candidate.relative_to(site_root)
        except ValueError:
            self.send_html(page("预览", "<p class='err'>非法路径</p><p><a href='/'>返回</a></p>"), 400)
            return
        if not candidate.is_file():
            self.send_html(page("预览", "<p class='err'>找不到预览文件，请先保存构建一次。</p><p><a href='/'>返回</a></p>"), 404)
            return
        data = candidate.read_bytes()
        content_type = "text/html; charset=utf-8"
        if candidate.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        try:
            self._do_POST()
        except Exception as exc:
            sys.stderr.write("POST error: %s\n" % exc)
            try:
                self.send_html(
                    page("错误", f"<p class='err'>保存失败：{html.escape(str(exc))}</p><p><a href='/'>返回</a></p>"),
                    500,
                )
            except Exception:
                pass

    def _do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/save":
            self.send_html(page("错误", "<p>不支持的操作</p>"), 405)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = {k: (v[0] if v else "") for k, v in parse_qs(raw, keep_blank_values=True).items()}

        original = safe_post_name(form.get("original_file", "")) or ""
        filename = safe_post_name(form.get("filename", ""))
        if not filename:
            # auto name for new posts
            filename = suggested_filename(form.get("title", "post"), form.get("date", ""))

        if original and filename != original:
            # keep locked rename from being spoofed easily; allow only same file when locked
            filename = original

        target = POSTS_DIR / filename
        POSTS_DIR.mkdir(parents=True, exist_ok=True)
        target.write_text(build_markdown(form), encoding="utf-8")

        ok, output = run_build()
        msg = "已保存并构建成功。" if ok else f"已保存，但构建失败：{output}"
        # redirect-style response with message on home
        self.send_html(render_home(message=msg, ok=ok))


def main() -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), AdminHandler)
    server.allow_reuse_address = True
    print(f"Admin editor: http://{HOST}:{PORT}/", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)


if __name__ == "__main__":
    main()
