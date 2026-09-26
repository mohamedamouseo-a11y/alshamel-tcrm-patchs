#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-EVOLUTION-RUNTIME-STATUS-BADGE-FIX-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
FRONT = ROOT / "client/src/pages/evolution/EvolutionV2Inbox.tsx"
ROUTER = ROOT / "server/evolutionV2Router.ts"

for p in (FRONT, ROUTER):
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

# --- Backend: add an explicit runtime reachability/status query ---
router = ROUTER.read_text(encoding="utf-8")
router0 = router

runtime_marker = "runtimeStatus: operatorProcedure.query"
if runtime_marker not in router:
    anchor = '''  overview: operatorProcedure.query(async ({ ctx }) => {
    const [status, settings, accounts] = await Promise.all([
      getWhatsAppEvolutionStatus(),
      getWhatsAppEvolutionAdminSettings(),
      listEvolutionV2Accounts(actorFromContext(ctx)),
    ]);
    return {
      release: "2.4.0-rc2",
      productionCandidate: true,
      status,
      settings,
      accounts,
      connectedAccounts: accounts.filter(item => item.isConnected).length,
      taraAccounts: accounts.filter(item => item.taraEnabled).length,
    };
  }),
'''
    if anchor not in router:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print("ERROR=ROUTER_OVERVIEW_ANCHOR_NOT_FOUND")
        sys.exit(2)

    runtime = '''  runtimeStatus: operatorProcedure.query(async () => {
    const status = await getWhatsAppEvolutionStatus();
    if (!status.configured) {
      return {
        apiOnline: false,
        configured: false,
        totalAccounts: 0,
        connectedAccounts: 0,
        reason: "not_configured" as const,
      };
    }

    try {
      const summaries = await listWhatsAppEvolutionInstanceSummaries();
      return {
        apiOnline: true,
        configured: true,
        totalAccounts: summaries.items.length,
        connectedAccounts: summaries.items.filter(item => item.isConnected === true).length,
        reason: null,
      };
    } catch (error) {
      console.error("[EvolutionV2] Runtime status check failed:", error);
      return {
        apiOnline: false,
        configured: true,
        totalAccounts: 0,
        connectedAccounts: 0,
        reason: "provider_unreachable" as const,
      };
    }
  }),
'''
    router = router.replace(anchor, anchor + runtime, 1)

if router != router0:
    backup(ROUTER)
    ROUTER.write_text(router, encoding="utf-8")
    changed.append("server/evolutionV2Router.ts")

# --- Frontend: distinguish provider reachability from account connection state ---
front = FRONT.read_text(encoding="utf-8")
front0 = front

accounts_query = '''  const accountsQ = trpc.evolutionV2.accounts.list.useQuery(undefined, { refetchInterval: 20000, refetchOnMount: "always", refetchOnWindowFocus: true, refetchOnReconnect: true, retry: false });
'''
runtime_query = accounts_query + '''  const runtimeStatusQ = trpc.evolutionV2.runtimeStatus.useQuery(undefined, { refetchInterval: 10000, refetchOnMount: "always", refetchOnWindowFocus: true, refetchOnReconnect: true, retry: 1 });
'''
if "trpc.evolutionV2.runtimeStatus.useQuery" not in front:
    if accounts_query not in front:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print("ERROR=FRONT_ACCOUNTS_QUERY_ANCHOR_NOT_FOUND")
        sys.exit(3)
    front = front.replace(accounts_query, runtime_query, 1)

old_state = '''  const connectedAccountCount = accounts.filter((account: any) => account.isConnected !== false).length;
  const evolutionOnline = connectedAccountCount > 0;
'''
new_state = '''  const fallbackConnectedAccountCount = accounts.filter((account: any) => account.isConnected === true).length;
  const connectedAccountCount = Number(runtimeStatusQ.data?.connectedAccounts ?? fallbackConnectedAccountCount);
  const evolutionApiOnline = runtimeStatusQ.data?.apiOnline === true;
  const evolutionStatusLoading = runtimeStatusQ.isLoading && !runtimeStatusQ.data;
  const evolutionStatusUnavailable = runtimeStatusQ.isError || (!runtimeStatusQ.isLoading && !runtimeStatusQ.data);
  const evolutionBadgeText = evolutionStatusLoading
    ? (isRTL ? "جارٍ التحديث" : "Updating")
    : evolutionStatusUnavailable
      ? (isRTL ? "حالة Evolution غير متاحة" : "Evolution status unavailable")
      : !evolutionApiOnline
        ? (isRTL ? "Evolution API غير متاح" : "Evolution API unavailable")
        : connectedAccountCount > 0
          ? (isRTL ? `Evolution متصل · ${connectedAccountCount} حساب` : `Evolution online · ${connectedAccountCount} connected`)
          : (isRTL ? "Evolution API متصل · لا توجد حسابات متصلة" : "Evolution API online · 0 connected");
  const evolutionBadgeOnline = evolutionApiOnline && connectedAccountCount > 0;
'''
if "const evolutionBadgeText =" not in front:
    if old_state not in front:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print("ERROR=FRONT_STATUS_STATE_ANCHOR_NOT_FOUND")
        sys.exit(4)
    front = front.replace(old_state, new_state, 1)

old_badge = '''<Badge variant={evolutionOnline ? "secondary" : "outline"} className={`rounded-full px-3 ${evolutionOnline ? "text-emerald-700" : "text-amber-700"}`}>{accountsQ.isLoading ? (isRTL ? "جارٍ التحديث" : "Updating") : evolutionOnline ? (isRTL ? "Evolution متصل" : "Evolution online") : (isRTL ? "Evolution غير متاح" : "Evolution offline")}</Badge>'''
new_badge = '''<Badge
  variant={evolutionBadgeOnline ? "secondary" : "outline"}
  className={`rounded-full px-3 ${
    evolutionStatusUnavailable
      ? "text-slate-600"
      : evolutionApiOnline
        ? evolutionBadgeOnline ? "text-emerald-700" : "text-amber-700"
        : "text-red-700"
  }`}
>{evolutionBadgeText}</Badge>'''
if ">{evolutionBadgeText}</Badge>" not in front:
    if old_badge not in front:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print("ERROR=FRONT_BADGE_ANCHOR_NOT_FOUND")
        sys.exit(5)
    front = front.replace(old_badge, new_badge, 1)

# Keep the manual Refresh action in sync with the new runtime status query.
old_refresh = '''  if (!targets.length) { conversationsQ.refetch(); accountsQ.refetch(); return; }'''
new_refresh = '''  if (!targets.length) { conversationsQ.refetch(); accountsQ.refetch(); runtimeStatusQ.refetch(); return; }'''
if old_refresh in front:
    front = front.replace(old_refresh, new_refresh, 1)

if front != front0:
    backup(FRONT)
    FRONT.write_text(front, encoding="utf-8")
    changed.append("client/src/pages/evolution/EvolutionV2Inbox.tsx")

# Final guards
router_final = ROUTER.read_text(encoding="utf-8")
front_final = FRONT.read_text(encoding="utf-8")

for marker in [
    "runtimeStatus: operatorProcedure.query",
    "apiOnline: true",
    "provider_unreachable",
]:
    if marker not in router_final:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=BACKEND_GUARD_MISSING:{marker}")
        sys.exit(6)

for marker in [
    "trpc.evolutionV2.runtimeStatus.useQuery",
    "Evolution API online · 0 connected",
    "Evolution API unavailable",
    "evolutionBadgeText",
]:
    if marker not in front_final:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=FRONTEND_GUARD_MISSING:{marker}")
        sys.exit(7)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + ";".join(changed))
print("BADGE_LOGIC=API_REACHABILITY_PLUS_CONNECTED_ACCOUNTS")
print("API_UNAVAILABLE_DISTINCT=YES")
print("ZERO_CONNECTED_DISTINCT=YES")
print("CONNECTED_COUNT_VISIBLE=YES")
print("DB_SCHEMA=UNCHANGED")
print("AUTH=UNCHANGED")
print("WHATSAPP_SESSIONS=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
