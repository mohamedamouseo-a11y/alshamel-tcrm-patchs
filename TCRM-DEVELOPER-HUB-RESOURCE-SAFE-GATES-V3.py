#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, re, shutil, sys

PATCH = "TCRM-DEVELOPER-HUB-RESOURCE-SAFE-GATES-V3"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
FILE = ROOT / "server/routes/developerHubGitHubClone.ts"

if not FILE.exists():
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print(f"ERROR=MISSING:{FILE}")
    sys.exit(1)

src = FILE.read_text(encoding="utf-8")
orig = src

# Accept any indentation/formatting and only touch the intended memory guard.
pattern = re.compile(
    r'if\s*\(\s*available\s*>\s*0\s*&&\s*available\s*<\s*MIN_GATE_AVAILABLE_BYTES\s*&&\s*swapFree\s*<\s*256\s*\*\s*1024\s*\*\s*1024\s*\)'
)
replacement = 'if (available > 0 && (available < MIN_GATE_AVAILABLE_BYTES || swapFree < 256 * 1024 * 1024))'

if replacement not in src:
    src, count = pattern.subn(replacement, src, count=1)
    if count != 1:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print("ERROR=MEMORY_GUARD_NOT_FOUND")
        sys.exit(2)

if src != orig:
    backup = Path("/tmp") / f"{FILE.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(FILE, backup)
    FILE.write_text(src, encoding="utf-8")

final = FILE.read_text(encoding="utf-8")
if replacement not in final:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=FINAL_GUARD_MISSING")
    sys.exit(3)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=server/routes/developerHubGitHubClone.ts")
print("MEMORY_GUARD=RAM_OR_SWAP")
print("SWAP_EXHAUSTED_BLOCKS_PUSH=YES")
print("FORMAT_INDEPENDENT=YES")
print("OTHER_GATES=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
