# 命令与数据契约

脚本仅用 Python 3.10+ 标准库。以下命令中的 SKILL_DIR、RUN、INPUT 等由 Codex 替换成实际绝对路径并正确引用。
JSON 使用 UTF-8，时间采用 ISO 8601。例子说明结构，example.com 为保留示例域名，不是研究证据。
把输入 JSON 放 RUN/work；用 shell 参数数组或结构化执行避免将用户内容拼成命令。含单引号的用户消息正确转义。

## 环境、初始化和恢复

```
python SKILL_DIR/scripts/workflow.py doctor
python SKILL_DIR/scripts/workflow.py init --run RUN --location "London, UK" --industry "bakery" --language en
python SKILL_DIR/scripts/workflow.py resume --run RUN
```

state.json 包含 schema_version、skill_version、target、stage、selected、历史事件及各阶段内容摘要。
历史 records 不覆盖。resume 报告校验问题，发现问题先恢复对应阶段，不直接编辑摘要。
stage 顺序为 search、choose_customer、analyze、propose_plan、approve_plan、build_demo、prepare_email、complete / email_needs_input。

## 线索导入

```
python SKILL_DIR/scripts/workflow.py normalize --input RAW_FILE --out RUN/work/pool.json
```

导入上游 title/category/review_rating/review_count/phone/website/address/emails/link/place_id 等实际字段。
输出 businesses 数组及稳定 id、原始文件 SHA256 与数量。没有名字的行跳过并报告。邮箱在 emails_unverified。
这一步不联网、不筛选商机。CSV/JSON Lines/JSON 数组均可。

## shortlist

```
python SKILL_DIR/scripts/workflow.py shortlist --run RUN --pool RUN/work/pool.json --input SHORTLIST_JSON
```

输入：
```json
{
  "coverage_note": "少于五家时必须说明真实原因；五家时可省略",
  "candidates": [{
    "business_id": "复制 pool 中实际 id",
    "priority": "high",
    "website_status": "reviewed",
    "reason": "具体推荐理由",
    "opportunity": "建议的 Demo 切入点",
    "contact_note": "公开联系情况或尚未找到",
    "evidence": [{"kind": "fact", "text": "已观察到的事实", "source_url": "https://example.com/", "observed_at": "2026-09-29T10:00:00Z"}]
  }]
}
```

1–5 家，不重复，必须属于 pool。priority 为 high/medium/low；website_status 为 reviewed/unreachable/not_found/not_reviewed。
evidence 的 fact 必须有 URL 和 observed_at；inference 必须有 basis；unknown 仅写清楚 text。
脚本把原始 business 数据嵌入候选记录。请勿用本示例事实充作生产数据。

## select

```
python SKILL_DIR/scripts/workflow.py select --run RUN --business-id ACTUAL_ID --message "用户实际选择原文"
```

只能在真实选择后调用；该命令撤销 analysis/plan/approval/demo/email 当前引用，旧文件保留。

## analysis

```
python SKILL_DIR/scripts/workflow.py analysis --run RUN --input ANALYSIS_JSON
```

```json
{
  "business_id": "当前选定 id",
  "summary": "业务、网站和推荐方向的摘要",
  "findings": [
    {"kind": "fact", "text": "有来源的观察", "source_url": "https://example.com/", "observed_at": "2026-09-29T10:00:00Z"},
    {"kind": "inference", "text": "可能的业务帮助", "basis": "说明由哪些事实推导"},
    {"kind": "unknown", "text": "无法核实的内容"}
  ],
  "contacts": [{"email": "hello@example.com", "source_url": "https://example.com/contact", "checked_at": "2026-09-29T10:00:00Z"}],
  "contact_note": "无 contacts 时必须写替代入口或没有找到",
  "materials": [{"description": "素材说明", "source_url": "https://example.com/", "usage_basis": "用途与使用依据"}]
}
```

可以增加分析字段，脚本保留它们。公开联系方式必须来源可追溯，不代表邮箱已验证送达。

## plan 和 approve-plan

只更新联系信息时用 `workflow.py contacts --run RUN --input CONTACTS_JSON`。
CONTACTS_JSON 含 business_id、contacts 数组（字段同 analysis.contacts），无邮箱时提供 contact_note。
这会替换当前联系列表并使旧邮件失效，但保留分析、方案批准和 Demo，便于制作完 Demo 后补充邮箱。
后续重新保存完整 analysis 会清除此覆盖列表。邮件以当前 contacts 记录为准，若无则使用 analysis.contacts。

```
python SKILL_DIR/scripts/workflow.py plan --run RUN --input PLAN_JSON
python SKILL_DIR/scripts/workflow.py approve-plan --run RUN --message "用户实际批准原文"
```

```json
{
  "business_id": "当前 id",
  "goal": "希望展示的业务价值",
  "pages": ["首页", "产品和预约演示区域"],
  "visual_direction": "具体品牌、排版和视觉方向",
  "interactions": ["选择产品、日期与时间，预览模拟请求"],
  "materials": "实际可用/缺失素材及安排",
  "demo_limits": "独立设计概念；不产生真实订单、付款或邮件",
  "delivery": "本地 Demo、截图；公开分享需用户可用托管"
}
```

plan 自动绑定 analysis 摘要。重新导入 plan 撤销旧批准与 Demo。审批语义由 Codex 对照真实会话判断，脚本只留痕。

## scaffold

```
python SKILL_DIR/scripts/workflow.py scaffold --run RUN --kind catalog --input CONFIG_JSON
```

kind 为 catalog/booking/quote；须有批准方案，已有 demo 目录则拒绝覆盖，应编辑现有文件。
```json
{
  "business_id": "当前 id",
  "name": "实际商家名称",
  "tagline": "品牌标题",
  "intro": "有依据的商家介绍",
  "address": "已核实地址或明确待核实说明",
  "items": [{"title": "实际产品或服务", "description": "已核实介绍或明确示意内容"}],
  "eyebrow": "可选短句",
  "collection_title": "可选分类标题",
  "note": "可选补充说明"
}
```

## demo-ready

```
python SKILL_DIR/scripts/workflow.py demo-ready --run RUN --input DEMO_JSON
```

```json
{
  "business_id": "当前 id",
  "source_path": "demo",
  "checks": {
    "desktop": {"passed": true, "evidence": "实际视口、检查方式和结果"},
    "mobile": {"passed": true, "evidence": "实际视口、检查方式和结果"},
    "core_flow": {"passed": true, "evidence": "实际操作和结果"},
    "content": {"passed": true, "evidence": "核对具体内容和素材"},
    "no_real_submission": {"passed": true, "evidence": "检查网络或实现确认无真实提交"}
  },
  "screenshots": [{"path": "screenshots/desktop.png", "caption": "当前完成的 Demo 桌面效果", "captured_at": "2026-09-29T10:00:00Z"}],
  "public_access": {"verified": false, "reason": "当前只有本地预览"}
}
```

只有实际检查成功才填 true。脚本验证结构、文件与摘要，不代替浏览器判断。
source_path、screenshots[].path 必须位于 RUN 内。截图不在源码目录内。
若公开访问已核实，public_access 使用：
```json
{"verified": true, "url": "https://actual-demo.example.com/", "no_login": true, "checked_at": "2026-09-29T10:00:00Z", "evidence": "实际访问权限与免登录证据"}
```
示例 URL 不能用于实际邮件。每次源码修改需重新检查和截图。

## email

```
python SKILL_DIR/scripts/workflow.py email --run RUN --input COPY_JSON --profile PROFILE_JSON
```

PROFILE_JSON：name、company、company_description、location、signature 为非空文本；from_email 可选。
```json
{
  "business_id": "当前 id",
  "demo_sha256": "复制 state.demo.sha256",
  "recipient": "公开查到且已保存至 analysis.contacts 的邮箱，没有则留空字符串",
  "subject": "个性化英文主题",
  "greeting": "英文称呼",
  "observation": "发现商家与有依据的网站观察",
  "demo_intro": "完成了什么",
  "business_value": "核心功能及预期帮助",
  "additional_value": "可选第二段价值，空则省略",
  "disclosure": "真实适用的独立概念、示意图与功能限制说明",
  "invitation": "可选自定义合作邀请；省略则沿用母版",
  "chinese_translation": "与最终完整英文一致的中文对照"
}
```

当前 demo 源码/截图必须未改变，copy 摘要匹配。recipient 有值时必须匹配已研究 contacts，不能插入猜测邮箱。
完整条件：公开来源收件人＋验证过的免登录分享链接＋有效截图＋当前 Demo 版本。
满足则 ready_for_user_review / complete；否则 needs_input / email_needs_input，仍保存材料但没有 EML。
EML 是草稿文件，未发出；不存在保证送达、自动写入邮箱草稿箱或邮件客户端普遍可导入的承诺。
