#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-WHATSAPP-UI-REMOVE-EVOLUTION-BRANDING-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
CLIENT = ROOT / "client/src"

if not CLIENT.exists():
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print(f"ERROR=MISSING:{CLIENT}")
    sys.exit(1)

TARGETS = [
    CLIENT / "pages/evolution/EvolutionV2Inbox.tsx",
    CLIENT / "pages/evolution/EvolutionV2Accounts.tsx",
    CLIENT / "pages/evolution/EvolutionV2Settings.tsx",
    CLIENT / "components/WhatsAppSettingsTab.tsx",
]

for p in TARGETS:
    if not p.exists():
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=MISSING:{p}")
        sys.exit(2)

def backup(path: Path):
    b = Path("/tmp") / f"{path.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(path, b)
    return b

replacements = {
    "Evolution API (WhatsApp Baileys)": "WhatsApp (Baileys)",
    ">Evolution API<": ">WHATSAPP<",

    '"Evolution API unavailable"': '"WhatsApp service unavailable"',
    '"Evolution API online · 0 connected"': '"WhatsApp service online · 0 connected"',
    '"Evolution status unavailable"': '"WhatsApp status unavailable"',
    '"Evolution online · ${connectedAccountCount} connected"': '"WhatsApp online · ${connectedAccountCount} connected"',
    '"Evolution online"': '"WhatsApp online"',
    '"Evolution offline"': '"WhatsApp offline"',

    '"Evolution API غير متاح"': '"خدمة واتساب غير متاحة"',
    '"Evolution API متصل · لا توجد حسابات متصلة"': '"خدمة واتساب متصلة · لا توجد حسابات متصلة"',
    '"حالة Evolution غير متاحة"': '"حالة واتساب غير متاحة"',
    '"Evolution متصل · ${connectedAccountCount} حساب"': '"واتساب متصل · ${connectedAccountCount} حساب"',
    '"Evolution متصل"': '"واتساب متصل"',
    '"Evolution غير متاح"': '"واتساب غير متاح"',

    '(isRTL ? "Evolution متصل" : "Evolution online")': '(isRTL ? "واتساب متصل" : "WhatsApp online")',
    '(isRTL ? "Evolution غير متاح" : "Evolution offline")': '(isRTL ? "واتساب غير متاح" : "WhatsApp offline")',
}

changed = []
for path in TARGETS:
    src = path.read_text(encoding="utf-8")
    original = src
    for old, new in replacements.items():
        src = src.replace(old, new)

    src = src.replace('"Evolution API"', '"WhatsApp"')
    src = src.replace("'Evolution API'", "'WhatsApp'")

    if src != original:
        backup(path)
        path.write_text(src, encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))

remaining = []
for path in CLIENT.rglob("*"):
    if path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        continue
    if "Evolution API" in text:
        for i, line in enumerate(text.splitlines(), 1):
            if "Evolution API" in line and ('"Evolution API' in line or "'Evolution API" in line or ">Evolution API<" in line):
                remaining.append(f"{path.relative_to(ROOT)}:{i}")

if remaining:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=VISIBLE_EVOLUTION_API_REMAINS:" + ",".join(remaining[:20]))
    sys.exit(3)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + (";".join(changed) if changed else "NONE"))
print("EVOLUTION_API_UI_TEXT=REMOVED")
print("WHATSAPP_BRANDING=ACTIVE")
print("INTERNAL_EVOLUTION_IDENTIFIERS=UNCHANGED")
print("BACKEND=UNCHANGED")
print("DB=UNCHANGED")
print("AUTH=UNCHANGED")
print("WHATSAPP_SESSIONS=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
