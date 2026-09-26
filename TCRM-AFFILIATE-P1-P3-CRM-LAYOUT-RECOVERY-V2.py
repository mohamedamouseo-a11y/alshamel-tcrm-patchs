#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, re, shutil, sys

PATCH = "TCRM-AFFILIATE-P1-P3-CRM-LAYOUT-RECOVERY-V2"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
AFF = ROOT / "client/src/pages/affiliate"
APP = ROOT / "client/src/App.tsx"

targets = [
    AFF / "MarketersPage.tsx",
    AFF / "CoursesPage.tsx",
    AFF / "SubscriptionsPage.tsx",
]

for p in [APP, *targets]:
    if not p.exists():
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=MISSING:{p}")
        sys.exit(1)

def backup(path: Path):
    b = Path("/tmp") / f"{path.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(path, b)
    return b

changed = []

for path in targets:
    src = path.read_text(encoding="utf-8")
    original = src

    if 'from "@/components/CRMLayout"' not in src:
        m = re.search(r'^(import[^\n]+\n)', src, flags=re.M)
        if not m:
            print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=IMPORT_ANCHOR_MISSING:{path.name}")
            sys.exit(2)
        src = src[:m.end()] + 'import CRMLayout from "@/components/CRMLayout";\n' + src[m.end():]

    if "<CRMLayout" not in src:
        m = re.search(r'(return\s*\(\s*)(<div\b)', src)
        if not m:
            print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=RETURN_ROOT_MISSING:{path.name}")
            sys.exit(3)
        src = src[:m.start(2)] + "<CRMLayout>\n" + src[m.start(2):]

        close_idx = src.rfind("</div>")
        if close_idx < 0:
            print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=ROOT_CLOSE_MISSING:{path.name}")
            sys.exit(4)
        src = src[:close_idx+6] + "\n</CRMLayout>" + src[close_idx+6:]

    if src.count("<CRMLayout") != src.count("</CRMLayout>"):
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=CRM_LAYOUT_BALANCE_FAILED:{path.name}")
        sys.exit(5)

    if src != original:
        backup(path)
        path.write_text(src, encoding="utf-8")
        changed.append(str(path.relative_to(ROOT)))

app = APP.read_text(encoding="utf-8")
app0 = app

# Normalize Subscriptions route to component prop for consistent routing/audit.
render_pat = re.compile(
    r'<Route\s+path="/affiliate-marketing/subscriptions"[^>]*>.*?</Route>|'
    r'<Route\s+path="/affiliate-marketing/subscriptions"[^\n]*/>',
    flags=re.S,
)
if '<Route path="/affiliate-marketing/subscriptions" component={SubscriptionsPage} />' not in app:
    replacement = '<Route path="/affiliate-marketing/subscriptions" component={SubscriptionsPage} />'
    if render_pat.search(app):
        app = render_pat.sub(replacement, app, count=1)
    else:
        generic = '<Route path="/affiliate-marketing" component={BDAdvancedSettings} />'
        if generic not in app:
            print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=SUBSCRIPTIONS_ROUTE_ANCHOR_MISSING")
            sys.exit(6)
        app = app.replace(generic, replacement + "\n" + generic, 1)

if app != app0:
    backup(APP)
    APP.write_text(app, encoding="utf-8")
    changed.append("client/src/App.tsx")

# Final guards
for path in targets:
    text = path.read_text(encoding="utf-8")
    if 'from "@/components/CRMLayout"' not in text or "<CRMLayout" not in text or "</CRMLayout>" not in text:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=FINAL_LAYOUT_GUARD:{path.name}")
        sys.exit(7)

final_app = APP.read_text(encoding="utf-8")
if '<Route path="/affiliate-marketing/subscriptions" component={SubscriptionsPage} />' not in final_app:
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=FINAL_SUBSCRIPTIONS_ROUTE_GUARD")
    sys.exit(8)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + (";".join(changed) if changed else "NONE"))
print("MARKETERS_LAYOUT=YES")
print("COURSES_LAYOUT=YES")
print("SUBSCRIPTIONS_LAYOUT=YES")
print("SUBSCRIPTIONS_ROUTE=COMPONENT")
print("BACKEND_DB_AUTH=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
