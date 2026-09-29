# 安装与环境

## 带环境检查的安装入口（1.0.1）

仓库 README 提供 Windows `scripts/setup.ps1` 与 macOS `scripts/setup.sh` 的下载执行命令。
这两个入口显示六阶段进度，安装可自动处理的依赖，备份并安装两个 Skill，最后调用
`scripts/check_environment.py --smoke-test` 验证一次真实抓取。
Windows 缺少 WSL/Ubuntu 时会给出管理员安装命令，完成首次用户名设置或重启后重新运行即可继续。
不会把仅有 `docker-desktop` 当作完整 Linux 工作环境，也不会自动修改 Docker Desktop 内部配置。
Docker 的首次授权和 WSL Integration 需要按终端提示完成。

这两个便捷入口使用默认 `~/.codex/skills`。自定义 CODEX_HOME 时，保留原安装方式安装两个 Skill，
准备相应运行环境，再手动执行检查器的 `--skills-dir` 和 `--report-dir` 参数。

报告位置：Windows `%LOCALAPPDATA%/overseas-web-prospecting/setup/environment-report.json`；
macOS `~/Library/Caches/overseas-web-prospecting/setup/environment-report.json`。
报告与原始验证结果留在用户电脑，不提交仓库。
开始获客时读取已有报告，Windows 使用报告内的 `wsl_distro`，显式转换 Skill 和输出路径。
Mac 若使用 Homebrew 的 node@24，将 `$(brew --prefix node@24)/bin` 加到当前命令的 PATH；不用永久更改用户 shell 配置。

- `ready`：那一次查询已获得至少一个带地图链接、评分和评论数的商家。它不保证以后查询成功，也不表示已提取评价正文。
- `dependencies_ok_crawl_unverified`：仅检查依赖，未验证抓取，不能宣称地图抓取可用。
- `needs_action` / `setup_in_progress`：未就绪，先处理报告或终端中指出的问题。

报告只是一次带时间的检查结果；开始新任务仍要按上游要求做代表查询。
环境阻塞时，先告知具体缺失项和恢复步骤。官网初筛可作为临时成果，但不要表述为完成了 Google Maps 抓取。

检查器可单独运行；不加 `--smoke-test` 不下载镜像、不启动爬虫。Windows 示例：

```powershell
python scripts/check_environment.py --wsl-distro Ubuntu --skills-dir "$env:USERPROFILE/.codex/skills" --report-dir ./work/setup-check --smoke-test
```

真实验证使用一个固定的悉尼烘焙店查询、深度 1、无代理、无额外评论提取。
镜像下载最多等待 10 分钟，启动后最多观察 10 分钟；失败保留结果，不自动停止或删除容器。
上游使用固定容器名，检测到已有活动任务时拒绝覆盖。完成既有任务后再验证。
入口 `-CheckOnly`（Windows）或 `--check-only`（Mac）不安装依赖和 Skill、不启动抓取，仍会下载检查器、保存检查报告。
WSL 工具包安装面向 Ubuntu/Debian；其他发行版自行准备工具后使用检查器。

## 安装

发行包根目录包含 overseas-web-prospecting/。放入 `$CODEX_HOME/skills`；未设置时为用户主目录下 `.codex/skills`。
也可执行 `python scripts/install.py`，仅安装本 Skill、不覆盖已有目录、不安装系统依赖。
若 Codex 尚未发现，刷新技能列表、重启或开新聊天。
首次执行 `python "SKILL_DIR/scripts/workflow.py" doctor`。需要 Python 3.10+；可用 Codex 已提供的实际解释器。
PATH 找不到不等于没有安装；不读取凭据文件诊断。

## 必需能力

- Codex 可正常使用，允许当前项目的执行与文件读写。
- google-maps-scraper Skill，来源 https://github.com/gosom/google-maps-scraper 。版本从本机入口读取。
- 上游所需 Docker、Node.js、bash；Windows 现有上游路径为 WSL。检查发行版内工具和 Docker 守护进程，
  Windows 上有 Node 不等于 WSL 内有 Node。Win 路径和 /mnt/c/... 路径在边界显式转换。
- 能访问 Google Maps 与当前目标官网的网络。
- 浏览器读取、交互和截图能力。优先当前 Codex 浏览器，按其技能与文档操作。

缺少抓取技能时说明将安装第三方依赖，使用官方入口 `npx skills add gosom/google-maps-scraper`，按实际提示选择 Codex。
系统安装、登录、重启和平台审批不能假装由 Skill 自动完成。不索要聊天中的代理密钥，不复制作者凭据。

## 浏览器备用路径

如果没有可用浏览器工具，但能本地执行 Node，可以使用项目 work/browser-tools/ 中的 Playwright。
先检查已有运行时，避免重复安装。需要时仅在任务目录安装：
`npm install --prefix RUN/work/browser-tools playwright`，再用对应 CLI 安装 Chromium。
如实说明可选下载与审批，记录实际安装版本；不改全局 Node 或 Skill 安装目录。
capture.mjs 的 --module 接受 Playwright index.mjs 绝对路径；playwright-core 还需 --executable 指定实际浏览器。
命令里的 SKILL_DIR、RUN、PORT 由 Codex 解析为实际值，不原样运行。不硬编码作者路径。

## 可选能力与首次引导

图片生成仅在方案需要且工具可用时使用。Sites/用户自有托管只用于分享链接；邮箱连接不属于第一版依赖。
先解决阻碍搜索的设置，同时收集区域行业；发件人资料到邮件阶段再问。
记录检查到的版本至 RUN/work/environment.json，之后只检查相关变化，不反复询问已配置项。
