#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-WHATSAPP-LATEST-MESSAGES-LIVE-HEAD-FIX-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
FILE = ROOT / "client/src/pages/evolution/EvolutionV2Inbox.tsx"

if not FILE.exists():
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print(f"ERROR=MISSING:{FILE}")
    sys.exit(1)

src = FILE.read_text(encoding="utf-8")
orig = src

def backup():
    b = Path("/tmp") / f"{FILE.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(FILE, b)

# 1) Older-page cursor must not drive the continuously-polled live query.
src = src.replace(
    '  const [beforeId, setBeforeId] = useState<number | null>(null);\n',
    '  const [loadingOlder, setLoadingOlder] = useState(false);\n',
    1,
)

src = src.replace(
    '  const messagesQ = trpc.evolutionV2.inbox.messages.useQuery({ conversationId: selectedId || 1, limit: 200, beforeId }, { enabled: Boolean(selectedId), refetchInterval: 6000, refetchOnMount: "always" });',
    '  const messagesQ = trpc.evolutionV2.inbox.messages.useQuery({ conversationId: selectedId || 1, limit: 200, beforeId: null }, { enabled: Boolean(selectedId), refetchInterval: 3000, refetchOnMount: "always", refetchOnWindowFocus: true, refetchOnReconnect: true });',
    1,
)

# 2) Selection reset should no longer maintain a persistent "old page" polling cursor.
src = src.replace(
    '    setBeforeId(null);\n    setMessages([]);',
    '    setMessages([]);',
    1,
)

# 3) Every polling response is the live/latest head. Merge it into any already-loaded older history.
old_effect = '''  useEffect(() => {
    const page = messagesQ.data as any;
    if (!page) return;
    const items = Array.isArray(page) ? page : page.items || [];
    setMessages(previous => beforeId ? mergeById(items, previous) : items);
    setMessagesHasOlder(Boolean(Array.isArray(page) ? false : page.hasMoreBefore));
  }, [messagesQ.data, beforeId]);
'''
new_effect = '''  useEffect(() => {
    const page = messagesQ.data as any;
    if (!page) return;
    const items = Array.isArray(page) ? page : page.items || [];
    // Always merge the live/latest head so loading older history never freezes new messages.
    setMessages(previous => mergeById(previous, items));
    if (!messages.length || messages[0]?.id === items[0]?.id) {
      setMessagesHasOlder(Boolean(Array.isArray(page) ? false : page.hasMoreBefore));
    }
  }, [messagesQ.data]);
'''
if old_effect not in src:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=MESSAGES_EFFECT_ANCHOR_MISSING")
    sys.exit(2)
src = src.replace(old_effect, new_effect, 1)

# 4) Load older history as an explicit one-shot fetch, separate from live polling.
old_loader = '''  function loadOlderMessages() { const first = messages[0]?.id; const el = messagesScrollRef.current; if (!first || !messagesHasOlder || !el) return; preserveScrollRef.current = { height: el.scrollHeight, top: el.scrollTop }; setBeforeId(Number(first)); }
'''
new_loader = '''  async function loadOlderMessages() {
    const first = messages[0]?.id;
    const el = messagesScrollRef.current;
    if (!selectedId || !first || !messagesHasOlder || !el || loadingOlder) return;
    preserveScrollRef.current = { height: el.scrollHeight, top: el.scrollTop };
    setLoadingOlder(true);
    try {
      const page: any = await utils.evolutionV2.inbox.messages.fetch({ conversationId: selectedId, limit: 200, beforeId: Number(first) });
      const items = Array.isArray(page) ? page : page?.items || [];
      setMessages(previous => mergeById(items, previous));
      setMessagesHasOlder(Boolean(Array.isArray(page) ? false : page?.hasMoreBefore));
    } catch (error: any) {
      preserveScrollRef.current = null;
      toast.error(error?.message || (isRTL ? "تعذر تحميل الرسائل الأقدم" : "Could not load older messages"));
    } finally {
      setLoadingOlder(false);
    }
  }
'''
if old_loader not in src:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=OLDER_LOADER_ANCHOR_MISSING")
    sys.exit(3)
src = src.replace(old_loader, new_loader, 1)

# 5) Button busy state should follow the explicit history request, not the live-head poll.
src = src.replace(
    'disabled={messagesQ.isFetching}>{messagesQ.isFetching ? <Loader2 className="mr-2 animate-spin" /> : null}',
    'disabled={loadingOlder}>{loadingOlder ? <Loader2 className="mr-2 animate-spin" /> : null}',
    1,
)

if src != orig:
    backup()
    FILE.write_text(src, encoding="utf-8")

final = FILE.read_text(encoding="utf-8")
guards = [
    'beforeId: null',
    'refetchInterval: 3000',
    'const [loadingOlder, setLoadingOlder] = useState(false);',
    'await utils.evolutionV2.inbox.messages.fetch',
    'setMessages(previous => mergeById(previous, items));',
]
for marker in guards:
    if marker not in final:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=GUARD_MISSING:{marker}")
        sys.exit(4)

if 'const [beforeId, setBeforeId]' in final or 'setBeforeId(' in final:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=STALE_BEFORE_ID_STATE_REMAINS")
    sys.exit(5)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=client/src/pages/evolution/EvolutionV2Inbox.tsx")
print("LATEST_POLLING=3000MS")
print("LATEST_HEAD_ALWAYS_POLLED=YES")
print("OLDER_HISTORY_SEPARATE_FETCH=YES")
print("OLDER_HISTORY_DOES_NOT_FREEZE_LATEST=YES")
print("BACKEND=UNCHANGED")
print("DB=UNCHANGED")
print("WHATSAPP_SESSION=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
