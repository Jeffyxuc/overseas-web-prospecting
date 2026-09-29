# 海外建站获客助手

一个供 Codex 使用的本地 Skill，将海外商家线索研究、网站诊断、Demo 制作和开发邮件整理为可继续执行的工作流。

## 工作流程

1. 用户提供区域和行业。
2. 使用 Google Maps Scraper 获取线索，初筛并呈现最多五家候选。
3. 用户选定商家，Codex 深入分析官网，提出 Demo 方案。
4. 用户确认方案后，制作网站 Demo，检查电脑/手机效果并截图。
5. 按标准邮件母版生成英文正文、中文对照、附图和邮件草稿。

任务资料保存在用户自己的目录，支持中断后继续。用户选择和方案批准是明确的决策节点。
本项目不提供公共后台服务，不自动发送邮件。

## 安装并检查环境：推荐新用户使用

命令会显示依赖检查、安装和抓取验证的进度。需要能访问 GitHub、软件源、Docker Hub 和 Google Maps。
先安装并登录 Codex。以下命令会安装缺失的软件，备份已有同名 Skill 后安装两个 Skill；首次运行可能下载较多内容。

**Windows：在普通 PowerShell 中粘贴这一行。**

```powershell
$p = Join-Path $env:TEMP 'overseas-web-setup.ps1'; Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/Jeffyxuc/overseas-web-prospecting/main/scripts/setup.ps1' -OutFile $p; if ($?) { powershell.exe -NoProfile -ExecutionPolicy Bypass -File $p }
```

只对这次安装进程使用执行策略参数，不永久修改系统策略。通过 Windows 自带的 winget 安装缺失的 Python、Git、Node.js、Docker Desktop。
缺少 winget 时提示安装 [App Installer](https://aka.ms/getwinget)。缺少 WSL/Ubuntu 时，会显示管理员应执行的 `wsl --install -d Ubuntu`；
完成首次设置、必要的重启后，回到普通 PowerShell 重跑同一条命令。已有 Ubuntu-24.04 等发行版时，可在末尾追加 `-Distro Ubuntu-24.04`。
脚本在指定 WSL 中补充 Bash、Node、npm、Python、curl 和 Git，随后检查该环境能否连接 Linux Docker 引擎。

**Mac：在终端中粘贴这一行。**

```bash
p=$(mktemp -t overseas-web-setup) && curl -fLSs https://raw.githubusercontent.com/Jeffyxuc/overseas-web-prospecting/main/scripts/setup.sh -o "$p" && /bin/bash "$p"
```

缺少 Homebrew 时调用其官方安装器；按需安装 Python、Git、Node.js 和 Docker Desktop。
系统密码、开发工具下载、Docker 首次提示需要用户按屏幕指引完成。

**显示 `READY` 才表示真实抓取验证通过。** 最后会进行一次悉尼烘焙店的小规模查询，只有容器正常结束，
且结果中至少一个商家带有地图链接、评分和评论数，才报告抓取可用。这不等于完成评价正文分析。
系统授权、重启或 Docker 的 WSL 集成设置无法保证一次全自动完成；遇到这些情况，脚本给出下一步，重跑后重新检查并继续。
Windows 的 Docker 集成入口见 [Docker 官方指引](https://docs.docker.com/desktop/features/wsl/)，WSL 安装见 [微软指引](https://learn.microsoft.com/en-us/windows/wsl/install)。

现有 Skill 备份、环境报告和测试结果保留在 Windows `%LOCALAPPDATA%/overseas-web-prospecting/setup`，
或 Mac `~/Library/Caches/overseas-web-prospecting/setup`。验证不会发送邮件或发布网站。
只想检查环境，可在 Windows 命令末尾加 `-CheckOnly`，Mac 命令末尾加 `--check-only`；这种模式不测试抓取。
自定义 CODEX_HOME、手动验证和失败恢复见 [安装与环境](references/setup.md)。

## 仅安装 Skill：Mac / Windows

先安装 **Node.js 22.20.0 或更高版本（含 npm/npx）**、**Git**，并确保可以使用 Codex。
Mac 的终端和 Windows 的命令提示符（CMD）使用同一条命令：

```sh
npx -y skills@1.7.0 add Jeffyxuc/overseas-web-prospecting -a codex -g --copy -y
```

Windows PowerShell 如果提示禁止运行 `npx.ps1`，使用下面这条等效命令，无需修改系统执行策略：

```powershell
npx.cmd -y skills@1.7.0 add Jeffyxuc/overseas-web-prospecting -a codex -g --copy -y
```

命令固定安装工具版本，自动下载本仓库的 Skill，安装到 Codex 用户级目录。
`--copy` 使用文件复制，避免 Windows 创建符号链接的权限要求；`-y` 跳过安装选择提示。
这里使用 [Vercel Skills CLI](https://github.com/vercel-labs/skills#install-a-skill) 的标准安装流程，
工具版本固定为 1.7.0，技能内容从本仓库当前默认分支获取。
重复运行可能更新或覆盖同名安装副本；有自行修改时请先保留副本。

**这条命令安装的是获客 Skill，不会自动安装 Docker、Python、WSL 等系统运行环境，也不会替你登录服务。**
Google Maps Scraper 是独立依赖，首次使用时由本 Skill 检查并引导安装、配置。
Mac / Windows 使用相同的 Skill 文件；本次已实测 Windows 项目级隔离安装，Mac 未在实机上验证。

## 安装后开始

重新加载 Codex 技能或新开聊天，输入：

> 使用 $overseas-web-prospecting，帮我寻找英国曼彻斯特适合提供建站服务的烘焙店。

也可以只说“使用海外建站获客助手”，让 Codex 引导你填写区域与行业。
完整使用步骤见 [使用说明](使用说明.md)，执行规则见 [SKILL.md](SKILL.md)。

不使用 npx 时，可下载仓库后使用包内 `scripts/install.py` 安装；该备用安装器拒绝覆盖已有同名目录。

## 环境依赖

- Codex 桌面端及可用的浏览器/文件/执行能力。
- Python 3.10+；核心记录与邮件脚本仅使用标准库。
- 独立安装的 [Google Maps Scraper](https://github.com/gosom/google-maps-scraper) Skill，以及其 Docker、Node.js 和对应 Windows WSL 运行环境。
- 可访问 Google Maps 与目标商家网站的网络。
- 公开分享 Demo 时使用用户自己的可用托管能力；本地预览不依赖公开托管。

本仓库未复制上游抓取项目源码，其实际运行指引以已安装上游版本为准。

## 内容

| 目录或文件 | 用途 |
| --- | --- |
| `SKILL.md` | 主流程与阶段切换 |
| `agents/` | Codex 显示信息 |
| `references/` | 筛选、分析、搭建、邮件、恢复及数据契约 |
| `scripts/` | 环境检查、进度管理、截图、邮件打包与安装 |
| `assets/` | 邮件母版与产品预订/服务预约/询价三类网站起点 |
| `package-manifest.json` | 1.0.1 Skill 文件摘要 |

不把客户资料、发件人资料、代理配置或本地任务成果提交到此仓库。

## 验证

```sh
python scripts/test_workflow.py
python scripts/test_environment.py
```

核心流程原有 19 项本地行为测试、三类模板 9 组浏览器场景已验证；新增环境检查器有独立的离线行为测试。
真实 Google Maps 抓取、公共部署、邮箱发送和全新用户配置未在本版完成验证。
示例测试使用明确的虚构数据，不能作为真实客户研究结果。详见 [验证说明](验证说明.md)。

没有找到公开邮箱或没有验证过的外部分享链接时，仅生成待补充材料。
邮件草稿不等于已发送，也不保证送达或成交。
