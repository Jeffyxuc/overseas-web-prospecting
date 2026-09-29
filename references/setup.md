# 安装与环境

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
