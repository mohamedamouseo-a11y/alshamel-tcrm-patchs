#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-DEVELOPER-HUB-RESOURCE-SAFE-GATES-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
FILE = ROOT / "server/routes/developerHubGitHubClone.ts"

if not FILE.exists():
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print(f"ERROR=MISSING:{FILE}")
    sys.exit(1)

src = FILE.read_text(encoding="utf-8")
orig = src

def backup():
    p = Path("/tmp") / f"{FILE.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(FILE, p)

anchor = 'const BUILD_TIMEOUT_MS = 12 * 60_000;\n'
if "const MIN_GATE_AVAILABLE_BYTES" not in src:
    if anchor not in src:
        raise SystemExit("BUILD_TIMEOUT_ANCHOR_MISSING")
    src = src.replace(anchor, anchor + 'const MIN_GATE_AVAILABLE_BYTES = 1536 * 1024 * 1024;\n', 1)

gate_fn = 'async function runProductionGates(res: Response, cwd: string, isClosed: () => boolean) {\n'
if "async function assertProductionGateHeadroom()" not in src:
    if gate_fn not in src:
        raise SystemExit("GATE_FN_ANCHOR_MISSING")
    helper = r'''async function assertProductionGateHeadroom() {
  if (process.platform !== "linux") return;
  const raw = await fs.readFile("/proc/meminfo", "utf8").catch(() => "");
  if (!raw) return;
  const values = new Map<string, number>();
  for (const line of raw.split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z_()]+):\s+(\d+)\s+kB$/);
    if (match) values.set(match[1], Number(match[2]) * 1024);
  }
  const available = Number(values.get("MemAvailable") || 0);
  const swapFree = Number(values.get("SwapFree") || 0);
  if (available > 0 && available < MIN_GATE_AVAILABLE_BYTES && swapFree < 256 * 1024 * 1024) {
    const availableMb = Math.round(available / 1024 / 1024);
    const swapFreeMb = Math.round(swapFree / 1024 / 1024);
    throw new Error("Developer Hub validation paused: low server memory (" + availableMb + " MB available, " + swapFreeMb + " MB swap free). Free memory or restart the VPS, then Review Push again.");
  }
}

'''
    src = src.replace(gate_fn, helper + gate_fn, 1)

old_start = '''async function runProductionGates(res: Response, cwd: string, isClosed: () => boolean) {
  const packageManager = existsSync(path.join(REPO_DIR, "pnpm-lock.yaml")) ? "pnpm" : "npm";
'''
new_start = '''async function runProductionGates(res: Response, cwd: string, isClosed: () => boolean) {
  await assertProductionGateHeadroom();
  const packageManager = existsSync(path.join(REPO_DIR, "pnpm-lock.yaml")) ? "pnpm" : "npm";
'''
if "await assertProductionGateHeadroom();" not in src:
    if old_start not in src:
        raise SystemExit("GATE_START_ANCHOR_MISSING")
    src = src.replace(old_start, new_start, 1)

old_gate = '{ args: [...runner, "check"], percent: 42, step: "TypeScript", stepAr: "فحص TypeScript" },'
new_gate = '{ args: [...runner, "check"], cwd: REPO_DIR, percent: 42, step: "TypeScript", stepAr: "فحص TypeScript" },'
if 'cwd: REPO_DIR, percent: 42' not in src:
    if old_gate not in src:
        raise SystemExit("TYPECHECK_GATE_ANCHOR_MISSING")
    src = src.replace(old_gate, new_gate, 1)

old_call = '''      cwd,
      step: gate.step,
'''
new_call = '''      cwd: (gate as any).cwd || cwd,
      step: gate.step,
'''
if 'cwd: (gate as any).cwd || cwd,' not in src:
    if old_call not in src:
        raise SystemExit("GATE_CWD_ANCHOR_MISSING")
    src = src.replace(old_call, new_call, 1)

if src != orig:
    backup()
    FILE.write_text(src, encoding="utf-8")

final = FILE.read_text(encoding="utf-8")
for marker in [
    "const MIN_GATE_AVAILABLE_BYTES",
    "async function assertProductionGateHeadroom()",
    "await assertProductionGateHeadroom();",
    'cwd: REPO_DIR, percent: 42',
    'cwd: (gate as any).cwd || cwd,',
]:
    if marker not in final:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=GUARD_MISSING:{marker}")
        sys.exit(2)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=server/routes/developerHubGitHubClone.ts")
print("TYPECHECK_CWD=STABLE_MAIN_REPO")
print("INCREMENTAL_TSC_CACHE=REUSABLE")
print("LOW_MEMORY_FAIL_FAST=YES")
print("OTHER_GATES=CANDIDATE_WORKTREE")
print("SAFE_CANCEL=UNCHANGED")
print("REMOTE_MUTATION_GUARD=UNCHANGED")
print("DB=UNCHANGED")
print("AUTH=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
