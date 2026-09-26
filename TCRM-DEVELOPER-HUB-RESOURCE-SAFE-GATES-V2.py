#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-DEVELOPER-HUB-RESOURCE-SAFE-GATES-V2"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
FILE = ROOT / "server/routes/developerHubGitHubClone.ts"

if not FILE.exists():
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print(f"ERROR=MISSING:{FILE}")
    sys.exit(1)

src = FILE.read_text(encoding="utf-8")
orig = src

old = '''  if (available > 0 && available < MIN_GATE_AVAILABLE_BYTES && swapFree < 256 * 1024 * 1024) {
    const availableMb = Math.round(available / 1024 / 1024);
    const swapFreeMb = Math.round(swapFree / 1024 / 1024);
    throw new Error(
      "Developer Hub validation paused: low server memory (" + availableMb + " MB available, " + swapFreeMb + " MB swap free). Free memory or restart the VPS, then Review Push again.",
    );
  }
'''
new = '''  if (available > 0 && (available < MIN_GATE_AVAILABLE_BYTES || swapFree < 256 * 1024 * 1024)) {
    const availableMb = Math.round(available / 1024 / 1024);
    const swapFreeMb = Math.round(swapFree / 1024 / 1024);
    throw new Error(
      "Developer Hub validation paused: unsafe server memory headroom (" + availableMb + " MB available, " + swapFreeMb + " MB swap free). Free memory/swap before Review Push.",
    );
  }
'''

if old not in src and "available < MIN_GATE_AVAILABLE_BYTES || swapFree < 256 * 1024 * 1024" not in src:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=MEMORY_GUARD_ANCHOR_NOT_FOUND")
    sys.exit(2)

if old in src:
    b = Path("/tmp") / f"{FILE.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(FILE, b)
    src = src.replace(old, new, 1)
    FILE.write_text(src, encoding="utf-8")

final = FILE.read_text(encoding="utf-8")
marker = "available < MIN_GATE_AVAILABLE_BYTES || swapFree < 256 * 1024 * 1024"
if marker not in final:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=FINAL_GUARD_MISSING")
    sys.exit(3)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=server/routes/developerHubGitHubClone.ts")
print("MEMORY_GUARD=RAM_OR_SWAP")
print("SWAP_EXHAUSTED_BLOCKS_PUSH=YES")
print("RAM_LOW_BLOCKS_PUSH=YES")
print("OTHER_GATES=UNCHANGED")
print("SAFE_CANCEL=UNCHANGED")
print("REMOTE_MUTATION_GUARD=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
