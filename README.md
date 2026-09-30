# 海外建站获客助手

供 **Codex 桌面端**使用的本地 Skill：找海外商家 → 选客户 → 分析官网 → 确认方案 → 搭建 Demo → 生成开发邮件包。无需作者维护服务器，不自动发送邮件。

## 让 Codex 帮你安装（推荐）

先安装并登录 Codex，在本地聊天中复制发送下面这段话。Windows 和 Mac 使用同一段指令，由 Codex 识别系统并选择安装入口，无需自己挑选终端命令。

```text
请按照 https://github.com/Jeffyxuc/overseas-web-prospecting 的 README 和 references/setup.md，为我安装最新版海外建站获客 Skill 及其运行环境。先识别我的操作系统和现有安装，再使用项目提供的对应安装入口，备份已有版本，复用可用依赖和本机网络配置，并保存后续可直接使用的运行设置。请直接完成安装，不要只给我操作教程；只有遇到必须由我处理的系统授权、密码、网络信息或重启时，再说明需要我做什么。不要让我在聊天中提供代理密码。安装后必须执行一次真实 Google Maps 抓取验收，确认正常结束且取得商家的地图链接、评分和评论数；未通过时如实说明原因和下一步，不要把仅安装好文件当作全部完成。最后用中文告知安装版本、验收结果，以及我在 Codex 中如何启动这个技能。
```

需要本机网络能够访问相关下载源和 Google Maps。系统授权、首次账户设置或重启仍可能需要本人操作；Mac 入口尚未实机验收。遇到这些步骤，Codex 会按项目说明引导继续。

## 自己在终端安装并验证环境

先安装并登录 Codex，准备能访问 GitHub、软件源、Docker Hub、Google Maps 的网络。在自己的电脑运行下面一行命令。安装会显示六阶段进度；系统授权、首次账户设置或重启按提示完成后，重跑同一条命令即可。

**Windows · 普通 PowerShell**

```powershell
$p = Join-Path $env:TEMP 'overseas-web-setup.ps1'; Invoke-WebRequest -UseBasicParsing 'https://raw.githubusercontent.com/Jeffyxuc/overseas-web-prospecting/main/scripts/setup.ps1' -OutFile $p; if ($?) { powershell.exe -NoProfile -ExecutionPolicy Bypass -File $p }
```

默认使用 WSL 2 + Ubuntu 内的 Docker Engine，按需安装 Windows Python/Node 和 Linux 抓取工具。缺少 Ubuntu 时会明确提示管理员安装命令；不用购买代理服务，也不强制安装 Docker Desktop。加入 Linux Docker 用户组会授予该账户控制 Docker 的权限。

已有正常运行的 Docker Desktop，可在命令末尾追加 `-Engine Desktop`，先开启其 Ubuntu WSL 集成；其他 Ubuntu 发行版可追加 `-Distro Ubuntu-24.04`。本入口面向 Ubuntu/Debian。不会重置现有 Docker 数据。

**Mac · 终端**

```bash
p=$(mktemp -t overseas-web-setup) && curl -fLSs https://raw.githubusercontent.com/Jeffyxuc/overseas-web-prospecting/main/scripts/setup.sh -o "$p" && /bin/bash "$p"
```

按需通过 Homebrew 安装 Python、Git、Node 和 Docker Desktop。按屏幕提示完成系统密码、开发工具和 Docker 首次授权。**Mac 入口已做语法与跨平台逻辑检查，尚未做 Mac 实机验收。**

安装器自动完成：

1. 检查依赖和实际运行环境，显示缺少项。
2. 下载两个 Skill 的原始压缩包，保留 Bash 换行；识别 `.agents/skills`、`.codex/skills` 和自定义 `CODEX_HOME`。
3. 备份旧副本，合并两个默认目录中的同名安装，避免旧版继续被加载；安装失败恢复原副本。
4. 保存本机运行配置，复用可用代理环境变量；不把代理内容输出到聊天或发布包。
5. 执行一次小规模真实地图抓取，保存本地报告和原始结果。

**只有显示 `READY`，才表示这次抓取正常结束，且确实取得地图链接、评分和评论数。** 这不表示评价正文已经读取，也不保证以后每一次查询都成功。

状态和备份保存在 `$CODEX_HOME/overseas-web-prospecting/`，默认是 `~/.codex/overseas-web-prospecting/`。实际技能目录写在其中的 `installation.json`。后续获客直接复用 `runtime.json`，不用每轮重新搭环境。

## 网络配置与失败恢复

默认复用已有本地配置，否则检查当前运行环境的 `HTTPS_PROXY` / `HTTP_PROXY`；没有则直连。不附带作者代理，不推荐或购买第三方服务。

- **已有代理但没有自动识别**：把一条 HTTP/HTTPS 代理 URL 存到本地文本文件。Windows 命令末尾追加 `-ProxyFile "文件绝对路径"`；Mac 追加 `--proxy-file "文件绝对路径"`。不要把账号密码粘贴到聊天。
- **希望直连抓取**：Windows 追加 `-Network direct`；Mac 追加 `--direct`。Docker 镜像下载仍使用 Docker 自己的网络设置。
- **只检查现有安装**：Windows 追加 `-CheckOnly`；Mac 追加 `--check-only`。不安装或更新软件、不发起抓取，保存依赖检查报告；WSL 模式可能启动已有 Docker 服务。
- **安装中断**：处理终端指出的问题，再运行同一条安装命令。旧 Skill 的备份保留。
- **下载镜像失败**：Docker 守护进程的代理和浏览器抓取代理是不同设置；Windows 独立引擎可自动配置，Mac/Desktop 按提示在 Docker 中配置。

代理只能在用户已有的网络能力范围内使用；WSL 必须能连接代理端口。完整恢复步骤见 [安装与环境](references/setup.md)。

## 安装后开始

刷新 Codex 技能或新开聊天，输入：

> 使用 $overseas-web-prospecting，帮我寻找英国曼彻斯特适合提供建站服务的烘焙店。

接下来只需选择客户、确认 Demo 方案，并在邮件阶段提供自己的发件人资料。候选卡片默认展示评分和评论数；没有拿到时必须报告原因并尝试补查，不能悄悄跳过地图研究。

默认交付本地 Demo、真实截图和英文邮件/中文对照。有公开收件邮箱和已验证分享链接时生成 EML 草稿；缺少时标记待补充。公开分享使用你自己的托管能力。邮件不会自动发送。

详见 [使用说明](使用说明.md)、[执行规则](SKILL.md) 和 [验证说明](验证说明.md)。

## 仅安装 Skill 文件（已有环境的用户）

可使用 Vercel Skills CLI。它可能安装到 `~/.agents/skills`，不能根据旧教程假定是 `.codex/skills`：

```sh
npx -y skills@1.7.0 add Jeffyxuc/overseas-web-prospecting -a codex -g --copy -y
```

PowerShell 可用 `npx.cmd` 替代 `npx`。这条命令只装本 Skill，不配置抓取环境；新用户请用上面的完整安装入口。也可下载完整仓库，用 `python scripts/install.py` 进行拒绝覆盖的手动安装。

## 开发与验证

当前版本 **1.1.0**。主流程在 `SKILL.md`，规则在 `references/`，工具在 `scripts/`，邮件母版和 Demo 起点在 `assets/`；`package-manifest.json` 保存发行文件摘要。

```sh
python -m unittest discover -s scripts -p 'test_*.py'
```

本版已在 Windows + Ubuntu WSL 的现有环境完成真实抓取验收：16 家商家全部带评分和评论数。离线测试覆盖安装备份/回滚、异常压缩包、代理设置、WSL 保活、空结果和失败抓取等。尚未验证全新电脑从零安装、Mac 实机、公开部署及邮件送达。

本仓库通过 Docker 调用 [Google Maps Scraper](https://github.com/gosom/google-maps-scraper)，没有复制抓取源码。个人代理、发件人和客户资料留在本机，不进入仓库。
