# initial_trial-blog

本地静态个人博客试验。文章存在 `posts/`，`build.py` 生成 `site/`。日常写作可用本机网页编辑器。

## 功能

- 首页 / 文章列表 / 标签归档
- 发布时间、标签、文末 AI 提炼
- **本机网页编辑器**（新建/编辑文章，自动构建）
- GitHub Pages 自动部署工作流（推送 `main` 后构建上线）

## 快速预览（只读）

打开 `site/index.html`，或：

```bash
python build.py
```

## 网页里写文章（本机）

**推荐：** 双击项目文件夹里的 `打开博客编辑器.bat`（约 2 秒后自动打开浏览器）。

或手动：

```bash
python admin_server.py
```

然后打开 <http://127.0.0.1:8766/>

- 只绑定本机，不暴露到公网  
- 保存后自动运行 `build.py`  
- 关掉黑色命令行窗口即停止编辑器  

## 推送到 GitHub

**推荐：** 双击 `推送到GitHub.bat`

- 第一次会让你粘贴 Token，并保存到本地 `.secrets/github_token`（已加入 `.gitignore`，不会上传）
- 之后再推送一般**不用再贴 Token**，更不用每次重新生成
- 只有 Token 过期/失效/权限不够时，删掉 `.secrets/github_token` 再推一次即可

推送成功后看 Actions 是否变绿，再刷新 Pages。

## 新建文章时的元数据

```markdown
---
title: 文章标题
date: 2026-09-15 14:30
tags: Vibe入门
summary: 一句话摘要
ai_takeaway: 一句话结论
ai_points: 要点1; 要点2; 要点3
ai_next: 下一步可以做什么
---

# 文章标题

正文从这里开始。
```

`ai_*` 写在文头元数据里：构建时读出并生成文末表格，不会在 build 时调用 AI。

## 目录说明

| 路径 | 作用 |
|------|------|
| `posts/` | Markdown 文章（真源） |
| `config.toml` | 站点名、文案、导航 |
| `CONVENTIONS.md` | 命名与标签约定 |
| `admin_server.py` | 本机网页编辑器 |
| `build.py` | 生成 `site/` |
| `site/` | 生成结果 |
| `.github/workflows/` | GitHub Pages 部署 |

## 部署到公网（GitHub Pages）

1. 安装 Git，并在本项目执行 `git init`（若尚未初始化）
2. 在 GitHub 新建空仓库，按提示 `git remote add` / `push`
3. 仓库 Settings → Pages → Source 选 **GitHub Actions**
4. 推送到 `main` 后，Actions 会运行 `python build.py` 并发布
5. 公开地址一般是：`https://<你的用户名>.github.io/<仓库名>/`

详细约定见 `CONVENTIONS.md`。内容充实（写长文）请你自己在编辑器里完成。
