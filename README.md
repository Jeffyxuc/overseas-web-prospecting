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

## 一键安装：Mac / Windows

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
| `package-manifest.json` | 1.0.0 发行包原始文件摘要 |

不把客户资料、发件人资料、代理配置或本地任务成果提交到此仓库。

## 验证

```sh
python scripts/test_workflow.py
```

19 项本地行为测试通过。三类模板在电脑与两种手机视口的 9 组浏览器场景通过。
真实 Google Maps 抓取、公共部署、邮箱发送和全新用户配置未在本版完成验证。
示例测试使用明确的虚构数据，不能作为真实客户研究结果。详见 [验证说明](验证说明.md)。

没有找到公开邮箱或没有验证过的外部分享链接时，仅生成待补充材料。
邮件草稿不等于已发送，也不保证送达或成交。
