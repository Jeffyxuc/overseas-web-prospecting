# 安装与环境（1.1.0）

## 默认路径与启动顺序

新用户使用 README 的 Windows / Mac 完整安装入口。只装 Skill 不等于装好抓取环境。
安装器读取 CODEX_HOME；未设置时识别已有 `.agents/skills`，否则用 `.codex/skills`。默认安装会把两个目录内旧的同名 Skill 移到备份，最后只保留一套生效副本。自定义 CODEX_HOME 时只操作其中的 skills，不合并其他安装。

本地状态统一保存在 `$CODEX_HOME/overseas-web-prospecting`，未设置时为 `~/.codex/overseas-web-prospecting`：

- installation.json：实际 skills_dir、版本、备份位置。
- runtime.json：运行发行版、引擎类型、工具路径、代理文件路径；无明文代理 URL。
- secrets/：本机网络配置，勿输出、上传、加入仓库或复制给其他用户。
- environment-report.json：最近一次环境检查结论。
- smoke-*/：安装验收的真实原始数据。

开始获客先读取 installation.json/runtime.json 和报告，执行 workflow.py doctor。按 runtime.json 使用 `run_maps.py`；不重装已正常工作的环境、不重复索要代理选择。代理来源和作者电脑互不关联。报告不存在时引导执行 README 安装命令。

状态含义：ready 是一次真实查询通过；dependencies_ok_crawl_unverified 只验证依赖；needs_action/setup_in_progress 尚未完成。历史 ready 不是以后每次查询的成功证明。

## Windows

默认是 WSL 2 Ubuntu 内的独立 Docker Engine（docker.io），支持 systemd。缺少发行版时在管理员 PowerShell 执行 `wsl --install -d Ubuntu`，完成首次账户设置、必要重启后，在普通 PowerShell 重跑 README 命令。缺少 winget 按提示安装 App Installer。

若旧发行版没有 systemd，在其 `/etc/wsl.conf` 的 `[boot]` 节合并 `systemd=true`，保留其他设置。保存其他 Linux 任务后重启该发行版再继续。不得为了安装擅自终止其他聊天的 WSL 任务。

普通 Linux 用户可能需要加入 docker 组，并启动新会话才能生效；安装器会提示。这意味着该账户拥有 root 等效的 Docker 控制能力。已有 Docker Desktop 集成时，可用 `-Engine Desktop` 复用，避免与独立引擎冲突。Desktop 必须自行启动并开启所选发行版的 WSL Integration。

工具需要在 WSL 内可用，不能用 Windows 的 Node/Docker 命令存在来代替。安装器从 ZIP 写入文件，避免 Git 的 autocrlf 把 Bash 变成 CRLF。现有脚本有换行错误时重跑新安装入口，不永久改变全局 Git 配置。

`run_maps.py` 在整个抓取期间保持 WSL 客户端存活，并在后续运行时启动已安装的 Docker 服务。退出 Codex/中断进程后不保证后台持续工作。

## Mac

完整入口准备 Homebrew、Python、Node、Git、Docker Desktop。保存实际 Homebrew Node 路径，后续程序自己补充 PATH，不依赖上一次安装终端的临时环境变量。不更改全局 shell 配置。

需要完成 Docker 首次提示。Mac 主机上的环回代理在容器内映射到 host.docker.internal；不假设 Docker Desktop 开启 host networking。Mac 实机仍待验收，不能写成已验证支持所有 Mac。

## 网络配置

默认 auto：优先复用上次的本地文件，首次读取运行环境 HTTP(S)_PROXY；没有则直连。修改代理时显式传本地文件：Windows `-ProxyFile PATH`，Mac `--proxy-file PATH`。文件只有一条 `http://` 或 `https://` URL，包含端口；有账号密码时自行写入并编码特殊字符，不在聊天输入。

当前 scraper 要求代理带用户名/密码。匿名 HTTP 代理会生成临时兼容字段，先实际验证 Google 连接成功才保存。该字段不是真实代理账户；若代理拒绝，明确失败，不能声称已配置。仅支持此路径的 HTTP(S) 代理；SOCKS-only 环境请使用代理软件的 HTTP 端口。

WSL 环回代理使用 Linux Docker host 网络；需要 WSL 本身能访问该端口，系统网络模式不同可能需要填写从 WSL 可达的地址。不会擅自改系统网络模式或防火墙。

镜像下载与抓取是两层网络。独立 WSL 引擎保存 daemon.json 的原配置备份，合并 proxies；只有没有活动容器时才重启，失败恢复配置。Desktop/Mac 的镜像下载代理在 Docker 设置中配置。

direct 模式只停用抓取代理，不移除系统或 Docker 自有代理，不删除旧私密文件。运行日志可能包含代理，禁止直接输出 docker logs/env/配置内容；诊断只能输出脱敏摘要。

## 手动检查和抓取

由 Codex 把 SKILL_DIR、PROFILE、REPORT、RUN 替换为实际绝对路径，再执行：

```sh
python "SKILL_DIR/scripts/check_environment.py" --profile "PROFILE" --report-dir "REPORT" --smoke-test
python "SKILL_DIR/scripts/run_maps.py" --profile "PROFILE" --query "bakeries in Manchester UK" --output-dir "RUN/work/crawl-01"
```

Mac 用实际 Python 3.10+ 解释器。PROFILE 默认为上述 runtime.json，也可省略 --profile。
检查器不加 --smoke-test 时不下载镜像、不启动抓取，但可启动已有 WSL Docker 服务。
真实验收查询为悉尼烘焙店，深度1、并发1。镜像下载和抓取各最多等待10分钟。
每次抓取使用唯一容器名，保存 crawl.json；发现其他活动获客抓取或上游固定容器时拒绝覆盖。超时保留容器和原始文件，按记录检查状态；不要重复启动、自动停止其他任务或删除现场。
仅容器正常退出且有商家才算抓取完成；验收还需要至少一条评分/评论数/地图链接。

## 浏览器与可选能力

Codex 浏览器能读取目标站和截图即可。缺少浏览器工具时可在 RUN/work/browser-tools 安装 Playwright；先检查已有运行时，避免重复安装。按需执行 `npm install --prefix RUN/work/browser-tools playwright`，再安装对应 Chromium。不得用真实表单测试提交。
`capture.mjs --module` 接受 Playwright index.mjs 绝对路径；playwright-core 还需 --executable。模板是起点，仍需按方案完成网站和实际浏览器验证。

图片生成、托管和邮箱连接不属于抓取必装依赖。母版已随包提供，发件人到邮件阶段再收集。系统授权/重启和平台审批不能假装自动完成。
