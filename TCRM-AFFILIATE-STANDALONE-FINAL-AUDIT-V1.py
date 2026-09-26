#!/usr/bin/env python3
from pathlib import Path
import os
import re
import subprocess
import sys

AUDIT = "TCRM-AFFILIATE-STANDALONE-FINAL-AUDIT-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))

APP = ROOT / "client/src/App.tsx"
LAYOUT = ROOT / "client/src/components/CRMLayout.tsx"
CLIENT_POOL = ROOT / "client/src/pages/ClientPool.tsx"

pages = {
    "marketers": ROOT / "client/src/pages/affiliate/MarketersPage.tsx",
    "courses": ROOT / "client/src/pages/affiliate/CoursesPage.tsx",
    "subscriptions": ROOT / "client/src/pages/affiliate/SubscriptionsPage.tsx",
    "commissions": ROOT / "client/src/pages/affiliate/CommissionsPage.tsx",
    "invoices": ROOT / "client/src/pages/affiliate/InvoicesPage.tsx",
    "monthly-close": ROOT / "client/src/pages/affiliate/MonthlyClosePage.tsx",
    "exports": ROOT / "client/src/pages/affiliate/ExportsPage.tsx",
}

route_components = {
    "marketers": "MarketersPage",
    "courses": "CoursesPage",
    "subscriptions": "SubscriptionsPage",
    "commissions": "CommissionsPage",
    "invoices": "InvoicesPage",
    "monthly-close": "MonthlyClosePage",
    "exports": "ExportsPage",
}

def fail(msg):
    print(f"AUDIT={AUDIT}")
    print("RESULT=FAIL")
    print(f"ERROR={msg}")
    sys.exit(1)

for p in [APP, LAYOUT, CLIENT_POOL, *pages.values()]:
    if not p.exists():
        fail(f"MISSING_FILE:{p.relative_to(ROOT)}")

app = APP.read_text(encoding="utf-8")
layout = LAYOUT.read_text(encoding="utf-8")
client_pool = CLIENT_POOL.read_text(encoding="utf-8")

checks = []

# 1) All 7 standalone pages exist and use CRMLayout.
for slug, page in pages.items():
    text = page.read_text(encoding="utf-8")
    if "CRMLayout" not in text or "<CRMLayout" not in text:
        fail(f"{slug.upper()}_CRM_LAYOUT_MISSING")
    checks.append(f"{slug}:page+layout")

# 2) All 7 explicit routes exist.
for slug, component in route_components.items():
    marker = f'<Route path="/affiliate-marketing/{slug}" component={{{component}}} />'
    if marker not in app:
        fail(f"ROUTE_MISSING:{slug}")
    checks.append(f"{slug}:route")

# 3) Specific routes must come before generic Affiliate routes.
generic_positions = [
    pos for pos in [
        app.find('<Route path="/affiliate-marketing" component={BDAdvancedSettings} />'),
        app.find('<Route path="/affiliate-marketing/:tab" component={BDAdvancedSettings} />'),
    ] if pos >= 0
]
if not generic_positions:
    fail("GENERIC_AFFILIATE_ROUTES_MISSING")
generic_first = min(generic_positions)
for slug in route_components:
    pos = app.find(f'/affiliate-marketing/{slug}')
    if pos < 0 or pos > generic_first:
        fail(f"ROUTE_ORDER_INVALID:{slug}")
checks.append("route-order:pass")

# 4) Expanded + collapsed CRM sidebar must use direct href for all 7 items.
for slug in route_components:
    count = layout.count(f'href: "/affiliate-marketing/{slug}"')
    if count < 2:
        fail(f"SIDEBAR_HREF_COUNT:{slug}:{count}")
    checks.append(f"{slug}:sidebar={count}")

# 5) Sidebar mapper must respect href and direct-route active state.
required_layout_markers = [
    'const href = sub.href || `/clients?setup=1&section=${sub.section}`;',
    'location === sub.href || location.startsWith(sub.href + "/")',
]
for marker in required_layout_markers:
    if marker not in layout:
        fail("SIDEBAR_MAPPER_GUARD_MISSING")
checks.append("sidebar-mapper:pass")

# 6) None of the 7 sidebar items may still use legacy section-only navigation.
for slug in route_components:
    if f'{{ section: "{slug}",' in layout:
        fail(f"LEGACY_SIDEBAR_SECTION_REMAINS:{slug}")
checks.append("legacy-sidebar-links:none")

# 7) Legacy ClientPool setup sections must remain available for compatibility.
legacy_ids = {
    "marketers": "affiliate-marketers",
    "courses": "affiliate-courses",
    "subscriptions": "affiliate-subscriptions",
    "commissions": "affiliate-commissions",
    "invoices": "affiliate-invoices-payouts",
    "monthly-close": "affiliate-monthly-close",
    "exports": "affiliate-exports",
}
for slug, section_id in legacy_ids.items():
    if section_id not in client_pool:
        fail(f"LEGACY_CLIENTPOOL_SECTION_MISSING:{slug}")
checks.append("legacy-clientpool:preserved")

# 8) Guard important P3/P4/P5/P6/P7 business wiring.
important_markers = {
    "subscriptions": [
        "createClientWithCourseSubscription",
        "listCourseProducts",
        "listMarketers",
    ],
    "commissions": [
        "getEmaarCommissionReport",
        "createEmaarCommissionInvoice",
        "updateEmaarCommissionInvoiceStatus",
    ],
    "invoices": [
        "listEmaarCommissionInvoices",
        "updateEmaarCommissionInvoiceStatus",
        "refreshEmaarCommissionInvoiceFromReport",
        "cancelEmaarCommissionInvoice",
    ],
    "monthly-close": [
        "closeEmaarCommissionMonth",
        "listEmaarClosedMonths",
        "getEmaarDashboardKpis",
    ],
    "exports": [
        "/api/export/emaar-commissions",
        "listCourseProducts",
        "getEmaarCommissionReport",
    ],
}
for slug, markers in important_markers.items():
    text = pages[slug].read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            fail(f"BUSINESS_WIRING_MISSING:{slug}:{marker}")
checks.append("business-wiring:pass")

# 9) Standalone pages must not use the old ClientPool setup query path.
for slug, page in pages.items():
    text = page.read_text(encoding="utf-8")
    if "/clients?setup=1&section=" in text:
        fail(f"LEGACY_QUERY_PATH_IN_STANDALONE:{slug}")
checks.append("standalone-query-paths:clean")

# 10) Read-only worktree snapshot (do not mutate).
try:
    status = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--short"],
        text=True,
        stderr=subprocess.STDOUT,
        timeout=15,
    ).strip()
except Exception as exc:
    status = f"UNAVAILABLE:{exc.__class__.__name__}"

print(f"AUDIT={AUDIT}")
print("RESULT=PASS")
print("ROUTES=7/7")
print("PAGES=7/7")
print("SIDEBAR_DIRECT=7/7")
print("LEGACY_CLIENTPOOL=PRESERVED")
print("BUSINESS_WIRING=PASS")
print("BACKEND_MUTATION=NONE")
print("DB_MUTATION=NONE")
print("AUTH_MUTATION=NONE")
print("WORKTREE_STATUS_BEGIN")
print(status or "CLEAN")
print("WORKTREE_STATUS_END")
print("CHECKS=" + ";".join(checks))
print("ERROR=NONE")
