#!/usr/bin/env python3
"""Local workflow records and mail packaging. Python 3.10+, standard library only."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import ipaddress
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from email.policy import SMTP
from urllib.parse import urlparse, urlunparse

VERSION = "1.0.1"
SKILL = Path(__file__).resolve().parent.parent


def now():
    return datetime.now(timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def text_field(doc, key):
    value = doc.get(key)
    require(isinstance(value, str) and value.strip(), f"Missing text field: {key}")
    return value.strip()


def url(value, public=False):
    if not isinstance(value, str):
        return False
    try:
        p = urlparse(value)
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
            return False
        if public:
            host = p.hostname.lower()
            if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "." not in host:
                return False
            try:
                if not ipaddress.ip_address(host).is_global:
                    return False
            except ValueError:
                pass
        return True
    except ValueError:
        return False


def email_ok(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+", value))


def timestamp(value):
    require(isinstance(value, str), "Timestamp must be ISO 8601 text")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid ISO 8601 timestamp")


def inside(root, rel):
    root = Path(root).resolve()
    p = (root / rel).resolve()
    require(p.is_relative_to(root), "Artifact must stay inside its run directory")
    return p


def load_run(root):
    state = read(Path(root) / "state.json")
    require(state.get("schema_version") == 1, "Unsupported state version")
    return state


def save(root, state, event, details=None):
    state["updated_at"] = now()
    state.setdefault("history", []).append({"at": now(), "event": event, "details": details})
    write(Path(root) / "state.json", state)


def artifact(root, state, name):
    ref = state.get(name)
    require(isinstance(ref, dict) and "path" in ref, f"Missing stage: {name}")
    doc = read(inside(root, ref["path"]))
    require(digest(doc) == ref["sha256"], f"{name} changed outside workflow; import it again")
    return doc


def record(root, state, name, doc):
    key = digest(doc)
    rel = f"records/{name}-{key[:16]}.json"
    write(inside(root, rel), doc)
    state[name] = {"path": rel, "sha256": key}


def invalidate(state, *names):
    for name in names:
        state.pop(name, None)


def doctor(args):
    checks = {"python": {"version": sys.version.split()[0], "ok": sys.version_info >= (3, 10)}}
    for name in ("node", "docker", "bash", "wsl"):
        exe = shutil.which(name)
        checks[name] = {"found_on_path": bool(exe)}
        if exe and name in ("node", "docker"):
            try:
                result = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
                checks[name]["version"] = result.stdout.strip()[:180]
            except (OSError, subprocess.TimeoutExpired):
                checks[name]["version"] = "unavailable"
    docker = shutil.which("docker")
    if docker:
        try:
            r = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=15)
            checks["docker"]["daemon_ready"] = r.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            checks["docker"]["daemon_ready"] = False
    codex = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    candidates = [codex / "skills/google-maps-scraper/SKILL.md", Path.home() / ".agents/skills/google-maps-scraper/SKILL.md"]
    if args.scraper_skill:
        candidates.insert(0, Path(args.scraper_skill) / "SKILL.md")
    found = next((p for p in candidates if p.is_file()), None)
    checks["scraper_skill"] = {"found": bool(found), "path": str(found) if found else None}
    print(json.dumps({"version": VERSION, "checks": checks, "manual_checks": ["Codex browser access and screenshot capability", "Network access to Google Maps and target sites", "Windows: verify Docker/Node/bash inside the selected WSL distribution", "Optional public hosting availability"], "note": "Read-only check; PATH absence is not proof of absence in WSL. No software installed."}, ensure_ascii=False, indent=2))


def init(args):
    root = Path(args.run).resolve()
    require(not (root / "state.json").exists(), "Run already exists; use resume")
    require(args.location.strip() and args.industry.strip(), "Location and industry are required")
    root.mkdir(parents=True, exist_ok=True)
    write(root / "state.json", {"schema_version": 1, "skill_version": VERSION, "created_at": now(), "updated_at": now(), "stage": "search", "target": {"location": args.location, "industry": args.industry, "language": args.language}, "history": []})
    print(str(root / "state.json"))


def first(doc, *keys):
    for key in keys:
        value = doc.get(key)
        if value is not None and value != "":
            return value
    return ""


def canonical_link(value):
    if not url(value):
        return ""
    p = urlparse(value)
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", p.query, ""))


def normalize(args):
    p = Path(args.input)
    content = p.read_text(encoding="utf-8-sig")
    if p.suffix.lower() == ".csv":
        rows = list(csv.DictReader(io.StringIO(content)))
    else:
        try:
            raw = json.loads(content)
            rows = raw if isinstance(raw, list) else raw.get("results", [raw])
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), "Expected CSV rows, JSON array or JSON Lines objects")
    businesses = {}
    skipped = 0
    for row in rows:
        name = str(first(row, "title", "name", "business_name")).strip()
        if not name:
            skipped += 1
            continue
        address = str(first(row, "address", "full_address")).strip()
        maps = str(first(row, "link", "maps_url", "google_maps_url"))
        place = str(first(row, "place_id", "cid", "data_id"))
        phone = str(first(row, "phone", "phone_number"))
        # Branches sharing a website or phone remain separate when their addresses differ.
        if place:
            identity = "place:" + place
        elif canonical_link(maps):
            identity = "maps:" + canonical_link(maps)
        elif address:
            identity = "address:" + name.casefold() + "|" + address.casefold()
        else:
            identity = "raw:" + digest(row)
        bid = "biz-" + hashlib.sha256(identity.encode()).hexdigest()[:16]
        emails = first(row, "emails", "email")
        if isinstance(emails, str):
            emails = re.split(r"[\s,;|]+", emails.strip("[]\"' "))
        if not isinstance(emails, list):
            emails = []
        doc = {"id": bid, "name": name, "category": first(row, "category", "categories"), "address": address, "maps_url": maps, "website": first(row, "website", "website_url"), "phone": phone, "rating": first(row, "review_rating", "rating"), "review_count": first(row, "review_count", "reviews_count"), "emails_unverified": sorted({x.strip("\"'").lower() for x in emails if isinstance(x, str) and email_ok(x.strip("\"'"))}), "imported_at": now()}
        if bid in businesses:
            existing = businesses[bid]
            existing["emails_unverified"] = sorted(set(existing["emails_unverified"] + doc["emails_unverified"]))
            for k, v in doc.items():
                if not existing.get(k) and v:
                    existing[k] = v
        else:
            businesses[bid] = doc
    output = {"schema_version": 1, "source_file": p.name, "source_sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "input_count": len(rows), "skipped_no_name": skipped, "businesses": list(businesses.values())}
    write(args.out, output)
    print(json.dumps({"count": len(businesses), "skipped": skipped, "out": str(args.out)}))


def evidence(item):
    require(item.get("kind") in ("fact", "inference", "unknown"), "Evidence kind must be fact/inference/unknown")
    text_field(item, "text")
    if item["kind"] == "fact":
        require(url(item.get("source_url")), "Fact needs source_url")
        timestamp(item.get("observed_at"))
    if item["kind"] == "inference":
        text_field(item, "basis")


def shortlist(args):
    state = load_run(args.run)
    pool = read(args.pool)
    businesses = {d["id"]: d for d in pool["businesses"]}
    doc = read(args.input)
    candidates = doc.get("candidates")
    require(isinstance(candidates, list) and 1 <= len(candidates) <= 5, "Shortlist needs 1–5 real candidates")
    require(len({c["business_id"] for c in candidates}) == len(candidates), "Duplicate shortlisted business")
    if len(candidates) < 5:
        text_field(doc, "coverage_note")
    for c in candidates:
        bid = text_field(c, "business_id")
        require(bid in businesses, "Candidate not found in imported pool")
        require(c.get("priority") in ("high", "medium", "low"), "Invalid priority")
        require(c.get("website_status") in ("reviewed", "unreachable", "not_found", "not_reviewed"), "Invalid website_status")
        text_field(c, "reason")
        text_field(c, "opportunity")
        require(isinstance(c.get("evidence"), list) and c["evidence"], "Candidate needs evidence")
        for item in c["evidence"]:
            evidence(item)
        c["business"] = businesses[bid]
    invalidate(state, "selected", "analysis", "contacts", "plan", "approval", "demo", "email")
    record(args.run, state, "pool", pool)
    record(args.run, state, "shortlist", doc)
    state["stage"] = "choose_customer"
    save(args.run, state, "shortlist")
    print("Shortlist saved. Present candidates and wait for the user's choice.")


def select(args):
    state = load_run(args.run)
    doc = artifact(args.run, state, "shortlist")
    require(args.business_id in {c["business_id"] for c in doc["candidates"]}, "Business is not shortlisted")
    require(args.message.strip(), "Record the user's actual selection message")
    invalidate(state, "analysis", "contacts", "plan", "approval", "demo", "email")
    state["selected"] = {"business_id": args.business_id, "user_message": args.message, "at": now()}
    state["stage"] = "analyze"
    save(args.run, state, "customer_selected", state["selected"])
    print("Selection saved.")


def selected(state, doc):
    require(state.get("selected"), "Wait for the user to select a customer")
    require(doc.get("business_id") == state["selected"]["business_id"], "Document belongs to another customer")


def analysis(args):
    state = load_run(args.run)
    doc = read(args.input)
    selected(state, doc)
    text_field(doc, "summary")
    require(isinstance(doc.get("findings"), list) and doc["findings"], "Analysis needs findings")
    for item in doc["findings"]:
        evidence(item)
    contacts = doc.get("contacts", [])
    require(isinstance(contacts, list), "contacts must be an array")
    for c in contacts:
        require(email_ok(c.get("email")), "Invalid contact email")
        require(url(c.get("source_url")), "Contact requires public source URL")
        timestamp(c.get("checked_at"))
    if not contacts:
        text_field(doc, "contact_note")
    invalidate(state, "contacts", "plan", "approval", "demo", "email")
    record(args.run, state, "analysis", doc)
    state["stage"] = "propose_plan"
    save(args.run, state, "analysis_saved")
    print("Analysis saved.")


def plan(args):
    state = load_run(args.run)
    artifact(args.run, state, "analysis")
    doc = read(args.input)
    selected(state, doc)
    for key in ("goal", "visual_direction", "materials", "demo_limits", "delivery"):
        text_field(doc, key)
    for key in ("pages", "interactions"):
        require(isinstance(doc.get(key), list) and all(isinstance(x, str) and x.strip() for x in doc[key]) and doc[key], f"{key} must be a nonempty text array")
    doc["analysis_sha256"] = state["analysis"]["sha256"]
    invalidate(state, "approval", "demo", "email")
    record(args.run, state, "plan", doc)
    state["stage"] = "approve_plan"
    save(args.run, state, "plan_saved")
    print("Present this plan and wait for the user's approval.")


def contacts(args):
    """Refresh researched contact channels without invalidating an approved design."""
    state = load_run(args.run)
    artifact(args.run, state, "analysis")
    doc = read(args.input)
    selected(state, doc)
    require(isinstance(doc.get("contacts"), list), "contacts must be an array")
    for c in doc["contacts"]:
        require(email_ok(c.get("email")), "Invalid contact email")
        require(url(c.get("source_url")), "Contact requires public source URL")
        timestamp(c.get("checked_at"))
    if not doc["contacts"]:
        text_field(doc, "contact_note")
    invalidate(state, "email")
    record(args.run, state, "contacts", doc)
    if "demo" in state:
        state["stage"] = "prepare_email"
    save(args.run, state, "contacts_updated")
    print("Contacts updated. Design approval preserved; regenerate the email package.")


def approve(args):
    state = load_run(args.run)
    artifact(args.run, state, "plan")
    require(args.message.strip(), "Record actual user approval; do not invent it")
    state["approval"] = {"plan_sha256": state["plan"]["sha256"], "user_message": args.message, "at": now()}
    state["stage"] = "build_demo"
    save(args.run, state, "plan_approved", state["approval"])
    print("Approved plan saved.")


def approved(root, state):
    artifact(root, state, "analysis")
    doc = artifact(root, state, "plan")
    require(doc["analysis_sha256"] == state["analysis"]["sha256"], "Analysis changed; prepare a new plan")
    require(state.get("approval", {}).get("plan_sha256") == state["plan"]["sha256"], "Current plan has not been approved")


def scaffold(args):
    state = load_run(args.run)
    approved(args.run, state)
    out = inside(args.run, "demo")
    require(not out.exists(), "Demo already exists; edit it in place, do not overwrite")
    config = read(args.input)
    selected(state, config)
    for key in ("name", "tagline", "intro", "address"):
        text_field(config, key)
    require(args.kind in ("catalog", "booking", "quote"), "Unknown starter")
    items = config.get("items")
    require(isinstance(items, list) and items, "Provide items with title and description")
    for item in items:
        text_field(item, "title")
        text_field(item, "description")
    config["kind"] = args.kind
    shutil.copytree(SKILL / "assets/demo-base", out)
    safe = json.dumps(config, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    (out / "config.js").write_text("window.DEMO = " + safe + ";\n", encoding="utf-8")
    invalidate(state, "demo", "email")
    save(args.run, state, "demo_scaffolded", {"kind": args.kind, "path": "demo"})
    print("Starter created. Customize and inspect it before demo-ready; scaffolding is not completion.")


def source_hash(root):
    root = Path(root)
    require(root.is_dir(), "Demo source directory missing")
    hashes = []
    excluded = {".git", "node_modules", ".sites-runtime", ".openai"}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part in excluded for part in rel.parts):
            continue
        require(not p.is_symlink(), "Demo source may not contain symlinks")
        if p.is_file():
            hashes.append([rel.as_posix(), hashlib.sha256(p.read_bytes()).hexdigest()])
    require(hashes, "Demo source is empty")
    return digest(hashes)


def image_type(path):
    blob = Path(path).read_bytes()
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if blob.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "webp"
    raise ValueError("Screenshot must be PNG, JPEG or WebP (checked by bytes)")


def demo_ready(args):
    state = load_run(args.run)
    approved(args.run, state)
    doc = read(args.input)
    selected(state, doc)
    source = inside(args.run, text_field(doc, "source_path"))
    require(source != Path(args.run).resolve(), "Source must be a subdirectory, separate from records and mail")
    for check in ("desktop", "mobile", "core_flow", "content", "no_real_submission"):
        result = doc.get("checks", {}).get(check)
        require(isinstance(result, dict) and result.get("passed") is True, f"Missing passed check: {check}")
        text_field(result, "evidence")
    shots = doc.get("screenshots")
    require(isinstance(shots, list) and shots, "Demo needs actual screenshots")
    for shot in shots:
        p = inside(args.run, text_field(shot, "path"))
        require(not p.is_relative_to(source), "Keep screenshots outside demo source")
        text_field(shot, "caption")
        timestamp(shot.get("captured_at"))
        shot["type"] = image_type(p)
        shot["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
    public = doc.get("public_access", {})
    if public.get("verified") is True:
        require(url(public.get("url"), public=True), "Public URL must be an external HTTP(S) address")
        text_field(public, "evidence")
        timestamp(public.get("checked_at"))
        require(public.get("no_login") is True, "External customer must not need an account")
    doc["source_sha256"] = source_hash(source)
    doc["plan_sha256"] = state["plan"]["sha256"]
    invalidate(state, "email")
    record(args.run, state, "demo", doc)
    state["stage"] = "prepare_email"
    save(args.run, state, "demo_verified")
    print("Demo verification recorded. Assertions must come from actual inspection, not this script.")


def current_demo(root, state):
    approved(root, state)
    doc = artifact(root, state, "demo")
    require(doc["plan_sha256"] == state["plan"]["sha256"], "Demo is from an older plan")
    require(source_hash(inside(root, doc["source_path"])) == doc["source_sha256"], "Demo source changed: repeat checks and refresh screenshots")
    for shot in doc["screenshots"]:
        require(hashlib.sha256(inside(root, shot["path"]).read_bytes()).hexdigest() == shot["sha256"], "Screenshot changed: record demo-ready again")
    return doc


def mail(args):
    state = load_run(args.run)
    demo = current_demo(args.run, state)
    analysis_doc = artifact(args.run, state, "analysis")
    contact_doc = artifact(args.run, state, "contacts") if "contacts" in state else analysis_doc
    copy = read(args.input)
    profile = read(args.profile)
    selected(state, copy)
    require(copy.get("demo_sha256") == state["demo"]["sha256"], "Mail copy must reference current demo record sha256")
    for key in ("name", "company", "company_description", "location", "signature"):
        text_field(profile, key)
    for key in ("subject", "greeting", "observation", "demo_intro", "business_value", "disclosure", "chinese_translation"):
        text_field(copy, key)
    for value in (copy["subject"], profile.get("from_email", ""), copy.get("recipient", "")):
        require("\r" not in value and "\n" not in value, "Mail header cannot contain newlines")
    if profile.get("from_email"):
        require(email_ok(profile["from_email"]), "Invalid sender email")
    recipient = copy.get("recipient", "").strip()
    contact = None
    if recipient:
        contact = next((c for c in contact_doc.get("contacts", []) if c["email"].lower() == recipient.lower()), None)
        require(contact, "Recipient must be present in researched contacts; never guess an address")
    public = demo.get("public_access", {})
    shared = public.get("verified") is True and public.get("no_login") is True
    blockers = []
    if not recipient:
        blockers.append("未找到公开收件邮箱")
    if not shared:
        blockers.append("Demo 外部免登录访问链接尚未验证")
    # Reject unfinished editorial placeholders while keeping templates themselves parameterized.
    for key in ("subject", "greeting", "observation", "demo_intro", "business_value", "disclosure", "chinese_translation"):
        require(not re.search(r"\{\{|\}\}|\bTODO\b|\bTBD\b", copy[key]), f"Unresolved placeholder in {key}")
    template = read(SKILL / "assets/email-template.json")
    intro = template["introduction"].format(**profile)
    cta = copy.get("invitation") or template["invitation"]
    link_text = "View your website demo →\n" + public["url"] if shared else "[Demo link pending — internal draft, do not send yet]"
    access = template["access"] if shared else ""
    paragraphs = [copy["greeting"], intro, copy["observation"], copy["demo_intro"], copy["business_value"]]
    if copy.get("additional_value"):
        paragraphs.append(copy["additional_value"])
    paragraphs += [link_text, access, copy["disclosure"], cta, "Best,\n" + profile["signature"]]
    paragraphs = [p for p in paragraphs if p]
    body = "\n\n".join(paragraphs) + "\n"
    shot = demo["screenshots"][0]
    source_image = inside(args.run, shot["path"])
    ext = shot["type"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    rel = f"email-packages/{stamp}"
    out = inside(args.run, rel)
    out.mkdir(parents=True, exist_ok=False)
    image_name = "demo-preview." + ext
    shutil.copy2(source_image, out / image_name)
    def render(image_src):
        parts = []
        for paragraph in paragraphs:
            if paragraph == link_text and shared:
                escaped = html.escape(public["url"], quote=True)
                parts.append(f'<p><a href="{escaped}">View your website demo →</a></p>')
                parts.append(f'<p><a href="{escaped}"><img src="{image_src}" alt="{html.escape(shot["caption"], quote=True)}" width="584" style="display:block;width:100%;max-width:584px;height:auto"></a></p>')
            else:
                parts.append("<p>" + html.escape(paragraph).replace("\n", "<br>") + "</p>")
        if not shared:
            parts.append(f'<img src="{image_src}" alt="Demo preview" width="584" style="max-width:100%;height:auto">')
        return '<!doctype html><html lang="en"><meta charset="utf-8"><title>' + html.escape(copy["subject"]) + '</title><body style="font:16px/1.65 Arial,sans-serif;color:#20251f"><main style="max-width:640px;margin:auto;padding:24px">' + "".join(parts) + "</main></body></html>"
    (out / "email.txt").write_text("To: " + recipient + "\nSubject: " + copy["subject"] + "\n\n" + body, encoding="utf-8")
    (out / "email.html").write_text(render(image_name), encoding="utf-8")
    (out / "中文对照.txt").write_text(copy["chinese_translation"] + "\n", encoding="utf-8")
    status = {"status": "needs_input" if blockers else "ready_for_user_review", "blockers": blockers, "recipient": recipient or None, "contact_source": contact, "demo_url": public.get("url") if shared else None, "demo_record_sha256": state["demo"]["sha256"], "sent": False, "note": "公开来源和格式检查不代表实际送达；没有执行邮件发送。"}
    if not blockers:
        msg = EmailMessage(policy=SMTP)
        msg["To"] = recipient
        if profile.get("from_email"):
            msg["From"] = profile["from_email"]
        msg["Subject"] = copy["subject"]
        msg["X-Unsent"] = "1"
        msg.set_content(body)
        msg.add_alternative(render("cid:demo-preview"), subtype="html")
        msg.get_payload()[1].add_related(source_image.read_bytes(), maintype="image", subtype=ext, cid="<demo-preview>", filename=image_name, disposition="inline")
        (out / "outreach-draft.eml").write_bytes(msg.as_bytes())
    write(out / "status.json", status)
    (out / "发送说明.md").write_text("# 邮件方案\n\n状态：" + status["status"] + "\n\n" + ("\n".join("- " + b for b in blockers) if blockers else "请核对收件人、正文、附图和链接。可复制正文或尝试用邮件客户端打开 EML；不同客户端对草稿导入的支持不同。") + "\n\n本包未发送邮件，也未验证邮箱实际送达能力。HTML 使用同目录图片；邮件 EML 使用内嵌图片。\n", encoding="utf-8")
    state["email"] = {"path": rel, "status": status["status"], "demo_sha256": state["demo"]["sha256"]}
    state["stage"] = "email_needs_input" if blockers else "complete"
    save(args.run, state, "email_packaged", {"path": rel, "status": status["status"]})
    print(json.dumps({"path": str(out), **status}, ensure_ascii=False, indent=2))


def resume(args):
    state = load_run(args.run)
    problems = []
    for name in ("pool", "shortlist", "analysis", "contacts", "plan"):
        if name in state:
            try:
                artifact(args.run, state, name)
            except (ValueError, OSError) as e:
                problems.append(str(e))
    if "demo" in state:
        try:
            current_demo(args.run, state)
        except (ValueError, OSError) as e:
            problems.append(str(e))
    print(json.dumps({"state": state, "integrity_issues": problems, "note": "Old files are retained as history. Use current state references only; no background work is implied."}, ensure_ascii=False, indent=2))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("doctor")
    d.add_argument("--scraper-skill")
    d.set_defaults(func=doctor)
    n = sub.add_parser("normalize")
    n.add_argument("--input", required=True)
    n.add_argument("--out", required=True)
    n.set_defaults(func=normalize)
    for name, func in [("init", init), ("shortlist", shortlist), ("select", select), ("analysis", analysis), ("contacts", contacts), ("plan", plan), ("approve-plan", approve), ("scaffold", scaffold), ("demo-ready", demo_ready), ("email", mail), ("resume", resume)]:
        c = sub.add_parser(name)
        c.add_argument("--run", required=True)
        c.set_defaults(func=func)
        if name in ("shortlist", "analysis", "contacts", "plan", "scaffold", "demo-ready", "email"):
            c.add_argument("--input", required=True)
        if name == "init":
            c.add_argument("--location", required=True)
            c.add_argument("--industry", required=True)
            c.add_argument("--language", default="en")
        if name == "shortlist":
            c.add_argument("--pool", required=True)
        if name in ("select", "approve-plan"):
            c.add_argument("--message", required=True)
        if name == "select":
            c.add_argument("--business-id", required=True)
        if name == "scaffold":
            c.add_argument("--kind", choices=("catalog", "booking", "quote"), required=True)
        if name == "email":
            c.add_argument("--profile", required=True)
    return p


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        args = parser().parse_args()
        args.func(args)
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as error:
        print("Error: " + str(error), file=sys.stderr)
        sys.exit(2)
