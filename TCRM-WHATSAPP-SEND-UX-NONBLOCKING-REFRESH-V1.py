#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-WHATSAPP-SEND-UX-NONBLOCKING-REFRESH-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
TARGET = ROOT / "client/src/pages/evolution/EvolutionV2Inbox.tsx"

if not TARGET.exists():
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print(f"ERROR=MISSING:{TARGET}")
    sys.exit(1)

src = TARGET.read_text(encoding="utf-8")

old = '''const sendReply = trpc.evolutionV2.inbox.reply.useMutation({ onSuccess: async () => { setReply(""); setReplyToId(null); await Promise.all([utils.evolutionV2.inbox.messages.invalidate(), utils.evolutionV2.inbox.conversations.invalidate()]); }, onError: e => toast.error(e.message) });'''

new = '''const sendReply = trpc.evolutionV2.inbox.reply.useMutation({ onSuccess: () => { setReply(""); setReplyToId(null); void Promise.all([utils.evolutionV2.inbox.messages.invalidate(), utils.evolutionV2.inbox.conversations.invalidate()]).catch(() => {}); }, onError: e => toast.error(e.message) });'''

if old not in src:
    if new in src:
        print(f"PATCH={PATCH}")
        print("APPLY=PASS")
        print("STATE=ALREADY_APPLIED")
        print("FILE=client/src/pages/evolution/EvolutionV2Inbox.tsx")
        print("SEND_PENDING_BLOCKS_ON_INVALIDATION=NO")
        print("BACKGROUND_REFRESH=YES")
        print("BACKEND=UNCHANGED")
        print("DB=UNCHANGED")
        print("AUTH=UNCHANGED")
        print("WHATSAPP_SESSION=UNCHANGED")
        print("COMMIT=NO")
        print("PUSH=NO")
        sys.exit(0)
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=ANCHOR_NOT_FOUND")
    sys.exit(2)

backup = Path("/tmp") / f"{TARGET.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
shutil.copy2(TARGET, backup)

src = src.replace(old, new, 1)
TARGET.write_text(src, encoding="utf-8")

check = TARGET.read_text(encoding="utf-8")
if old in check or new not in check:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=VERIFY_FAILED")
    sys.exit(3)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILE=client/src/pages/evolution/EvolutionV2Inbox.tsx")
print("SEND_PENDING_BLOCKS_ON_INVALIDATION=NO")
print("BACKGROUND_REFRESH=YES")
print("BACKEND=UNCHANGED")
print("DB=UNCHANGED")
print("AUTH=UNCHANGED")
print("WHATSAPP_SESSION=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
