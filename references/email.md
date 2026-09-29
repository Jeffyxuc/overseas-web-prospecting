# 邮件规则

读取 assets/email-template.json，沿用用户 2026-09-28 确认的 Bakers Dozen 邮件段落与温和语气。
分发包不携带原发件人姓名、公司、地址、邮箱或原客户邮箱。
第一次邮件前收集 name、company、company_description（如 a web design studio）、location、signature，
from_email 可选。个体按真实个人品牌和身份填写，不索取密码。资料放用户 RUN/work/sender-profile.json 或其指定的私有文件。

## 个性化

- 自我介绍真实。
- 发现与观察有来源：“评价很好”不可套用到没有查看评价的客户。
- Demo 只介绍实际完成的功能。没有使用原 Logo 就不写保留 Logo。
- 价值写预期方便的路径，不承诺营收、排名或转化率。
- 链接和附图对应当前版本；只有验证免登录才保留该句。
- 声明独立概念与模拟范围；只有实际存在 AI 图才说明 AI 图。
- 沿用邀请回复与正式开发合作；按行业调整 shop 等词。

中文对照覆盖最终英文全部段落、签名、链接和声明；脚本不自动翻译，Codex 负责核对。
demo_sha256 来自 state.demo.sha256。仅改文字也需引用当前 Demo，不能用旧邮件冒充最新版本。

## 联系与打包

优先官网公开业务邮箱，其他商家自有页面须说明来源并核对身份。
emails_unverified 不能自动升级为公开核实；必须找到具体来源并加入 analysis.contacts。
不推导或猜测邮箱，格式/域名/公开来源均不代表一定送达。
`workflow.py email --run RUN --input COPY_JSON --profile PROFILE_JSON` 生成正文、HTML、中文对照、截图、状态与发送说明。
收件人和外部链接齐全时生成带 CID 图片的 EML，图片 MIME 按文件头决定。
HTML 与相邻图片一起使用；EML 自包含，但不同邮件客户端导入支持不同，也不等于存入邮箱草稿箱。
无邮箱或无分享链接时生成待补充材料，不创建容易误发的 EML。
交付时完整展示正文与附图，提供文件链接并说明状态。本包没有 SMTP 或发送函数。
用户另行要求发送时才核对当前版本、可用邮箱工具和授权，不自动群发或创建跟进任务。
