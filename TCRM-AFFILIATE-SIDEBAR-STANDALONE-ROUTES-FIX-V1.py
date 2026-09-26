#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os
import shutil
import sys

PATCH = "TCRM-AFFILIATE-SIDEBAR-STANDALONE-ROUTES-FIX-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
TARGET = ROOT / "client/src/components/CRMLayout.tsx"

if not TARGET.exists():
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print(f"ERROR=TARGET_NOT_FOUND:{TARGET}")
    sys.exit(1)

src = TARGET.read_text(encoding="utf-8")
original = src

routes = {
    "marketers": "/affiliate-marketing/marketers",
    "courses": "/affiliate-marketing/courses",
    "subscriptions": "/affiliate-marketing/subscriptions",
    "commissions": "/affiliate-marketing/commissions",
}

changes = []
for section, href in routes.items():
    legacy = f'{{ section: "{section}",'
    modern = f'{{ href: "{href}",'
    count_legacy = src.count(legacy)
    if count_legacy:
        src = src.replace(legacy, modern)
        changes.append(f"{section}:{count_legacy}")

# Guard: both expanded and collapsed Affiliate lists must resolve through href.
missing = []
for section, href in routes.items():
    count = src.count(f'href: "{href}"')
    if count < 2:
        missing.append(f"{section}={count}")

if missing:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=ROUTE_GUARD_FAILED:" + ",".join(missing))
    sys.exit(2)

# Existing mapper must support href fallback and standalone active-state handling.
required_markers = [
    'const href = sub.href || `/clients?setup=1&section=${sub.section}`;',
    'location === sub.href || location.startsWith(sub.href + "/")',
]
for marker in required_markers:
    if marker not in src:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print("ERROR=MAPPER_GUARD_MISSING:" + marker)
        sys.exit(3)

if src == original:
    print(f"PATCH={PATCH}")
    print("APPLY=PASS")
    print("CHANGED=NO")
    print("STATUS=ALREADY_APPLIED")
    sys.exit(0)

backup = Path("/tmp") / f"CRMLayout.tsx.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
shutil.copy2(TARGET, backup)
TARGET.write_text(src, encoding="utf-8")

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("CHANGED=YES")
print("FILE=client/src/components/CRMLayout.tsx")
print("ROUTES=marketers,courses,subscriptions,commissions")
print(f"BACKUP={backup}")
print("BUILD_REQUIRED=YES")
print("COMMIT=NO")
print("PUSH=NO")
