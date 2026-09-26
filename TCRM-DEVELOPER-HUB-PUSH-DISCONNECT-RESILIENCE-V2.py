#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-DEVELOPER-HUB-PUSH-DISCONNECT-RESILIENCE-V2"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
BACK = ROOT / "server/routes/developerHubGitHubClone.ts"
FRONT = ROOT / "client/src/components/DeveloperHubTab.tsx"

for p in (BACK, FRONT):
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

# ---------------- Backend ----------------
src = BACK.read_text(encoding="utf-8")
orig = src

globals_old = '''let operationRunning = false;
let activeChild: ChildProcess | null = null;
let remoteMutationStarted = false;
'''
globals_new = '''let operationRunning = false;
let activeChild: ChildProcess | null = null;
let remoteMutationStarted = false;
let cancelRequested = false;
'''
if "let cancelRequested = false;" not in src:
    if globals_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=BACKEND_GLOBALS_ANCHOR_MISSING")
        sys.exit(2)
    src = src.replace(globals_old, globals_new, 1)

lock_old = '''  operationRunning = true;
  lastOperationStatus = { state: "running", step: "Acquired lock", percent: 5 };
'''
lock_new = '''  operationRunning = true;
  cancelRequested = false;
  lastOperationStatus = { state: "running", step: "Acquired lock", percent: 5 };
'''
if "cancelRequested = false;\n  lastOperationStatus" not in src:
    if lock_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=LOCK_ANCHOR_MISSING")
        sys.exit(3)
    src = src.replace(lock_old, lock_new, 1)

release_old = '''        activeChild = null;
        remoteMutationStarted = false;
        operationRunning = false;
        if (lastOperationStatus.state === "running") lastOperationStatus = { state: "idle" };
'''
release_new = '''        activeChild = null;
        remoteMutationStarted = false;
        cancelRequested = false;
        operationRunning = false;
        if (lastOperationStatus.state === "running") lastOperationStatus = { state: "idle" };
'''
if "remoteMutationStarted = false;\n        cancelRequested = false;" not in src:
    if release_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=RELEASE_ANCHOR_MISSING")
        sys.exit(4)
    src = src.replace(release_old, release_new, 1)

stream_old = '''  if (options.isClosed()) throw new Error("Operation cancelled before the next step.");
  sendEvent(res, { type: "progress", step: options.step, stepAr: options.stepAr, percent: options.percent });
'''
stream_new = '''  if (options.isClosed()) throw new Error("Operation cancelled before the next step.");
  lastOperationStatus = { state: "running", step: options.step, stepAr: options.stepAr, percent: options.percent };
  sendEvent(res, { type: "progress", step: options.step, stepAr: options.stepAr, percent: options.percent });
'''
if "lastOperationStatus = { state: "running", step: options.step" not in src:
    if stream_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=STREAM_STATUS_ANCHOR_MISSING")
        sys.exit(5)
    src = src.replace(stream_old, stream_new, 1)

closed_old = '''    const isClosed = () => clientClosed;
    sendEvent(res, { type: "progress", step: "Verified review", stepAr: "تم اعتماد المراجعة", percent: 10 });
'''
closed_new = '''    // Transport loss must never cancel a reviewed operation. Only Safe Cancel may do that.
    const isClosed = () => cancelRequested;
    sendEvent(res, { type: "progress", step: "Verified review", stepAr: "تم اعتماد المراجعة", percent: 10 });
'''
if "const isClosed = () => cancelRequested;" not in src:
    if closed_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=CANCEL_SEPARATION_ANCHOR_MISSING")
        sys.exit(6)
    src = src.replace(closed_old, closed_new, 1)

success_old = '''    await audit({ action: `github.${action}`, actorUserId: user.id, actorEmail: user.email, repo: state.repo, branch: state.branch, result: "success", expectedAction: review.expectedAction, fingerprint: review.fingerprint, commit: result.newSha, localAligned: result.localAligned, statePersisted, selectedFiles: executionReview.includedFiles });
    if (!clientClosed) {
      sendEvent(res, { type: "done", action, expectedAction: review.expectedAction, commit: result.newSha, localAligned: result.localAligned, lastSyncAt: completedAt, statePersisted });
    lastOperationStatus = { state: "success", step: "Completed", commit: result.newSha, finishedAt: completedAt };
      res.end();
    }
'''
success_new = '''    await audit({ action: `github.${action}`, actorUserId: user.id, actorEmail: user.email, repo: state.repo, branch: state.branch, result: "success", expectedAction: review.expectedAction, fingerprint: review.fingerprint, commit: result.newSha, localAligned: result.localAligned, statePersisted, selectedFiles: executionReview.includedFiles });
    // Persist terminal success even if the browser/SSE connection disappeared.
    lastOperationStatus = { state: "success", step: "Completed", commit: result.newSha, finishedAt: completedAt };
    if (!clientClosed) {
      sendEvent(res, { type: "done", action, expectedAction: review.expectedAction, commit: result.newSha, localAligned: result.localAligned, lastSyncAt: completedAt, statePersisted });
      res.end();
    }
'''
if "Persist terminal success even if the browser/SSE connection disappeared." not in src:
    if success_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=SUCCESS_STATUS_ANCHOR_MISSING")
        sys.exit(7)
    src = src.replace(success_old, success_new, 1)

cancel_old = '''  terminateActiveChild();
  res.json({ ok: true });
});
'''
cancel_new = '''  cancelRequested = true;
  terminateActiveChild();
  res.json({ ok: true });
});
'''
if "cancelRequested = true;\n  terminateActiveChild();" not in src:
    if cancel_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=CANCEL_ENDPOINT_ANCHOR_MISSING")
        sys.exit(8)
    src = src.replace(cancel_old, cancel_new, 1)

if src != orig:
    backup(BACK)
    BACK.write_text(src, encoding="utf-8")
    changed.append("server/routes/developerHubGitHubClone.ts")

# ---------------- Frontend ----------------
src = FRONT.read_text(encoding="utf-8")
orig = src

warning_old = '''        addLog(isRTL ? "انقطع الاتصال، جارٍ التحقق من حالة العملية..." : "Connection lost, checking operation status...", "warning");
'''
warning_new = '''        addLog(isRTL ? "انقطع اتصال الشاشة فقط؛ العملية مستمرة على الخادم وجارٍ متابعة حالتها..." : "Screen connection lost; the server operation is still running and status recovery has started...", "warning");
'''
if warning_old in src:
    src = src.replace(warning_old, warning_new, 1)

loop_old = '''        for (let i = 0; i < 60; i++) {
'''
loop_new = '''        // Production gates can legitimately run for many minutes; keep recovery alive for 15 minutes.
        for (let i = 0; i < 450; i++) {
'''
if "for (let i = 0; i < 450; i++)" not in src:
    if loop_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=FRONT_RECOVERY_LOOP_ANCHOR_MISSING")
        sys.exit(9)
    src = src.replace(loop_old, loop_new, 1)

idle_old = '''            } else if (s.state === "idle" && i > 2) {
              addLog(isRTL ? "انتهت العملية دون نتيجة واضحة" : "Operation ended without clear result", "warning");
              recovered = true; break;
'''
idle_new = '''            } else if (s.state === "idle" && i > 10) {
              addLog(isRTL ? "الخادم لا يسجل عملية نشطة؛ جارٍ تحديث حالة GitHub قبل إنهاء المتابعة." : "No active server operation is recorded; refreshing GitHub state before ending recovery.", "warning");
              await loadAll();
              recovered = true; break;
'''
if "s.state === "idle" && i > 10" not in src:
    if idle_old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=FRONT_IDLE_ANCHOR_MISSING")
        sys.exit(10)
    src = src.replace(idle_old, idle_new, 1)

if src != orig:
    backup(FRONT)
    FRONT.write_text(src, encoding="utf-8")
    changed.append("client/src/components/DeveloperHubTab.tsx")

# ---------------- Guards ----------------
back = BACK.read_text(encoding="utf-8")
front = FRONT.read_text(encoding="utf-8")

for marker in [
    "let cancelRequested = false;",
    "const isClosed = () => cancelRequested;",
    "Persist terminal success even if the browser/SSE connection disappeared.",
    "cancelRequested = true;",
    "lastOperationStatus = { state: \"running\", step: options.step",
]:
    if marker not in back:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=BACKEND_GUARD_MISSING:{marker}")
        sys.exit(11)

for marker in [
    "for (let i = 0; i < 450; i++)",
    "Screen connection lost; the server operation is still running",
    's.state === "idle" && i > 10',
]:
    if marker not in front:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=FRONTEND_GUARD_MISSING:{marker}")
        sys.exit(12)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + ";".join(changed))
print("SSE_DISCONNECT_CANCELS_OPERATION=NO")
print("SAFE_CANCEL_PRESERVED=YES")
print("REMOTE_MUTATION_GUARD_PRESERVED=YES")
print("OPERATION_STATUS_PROGRESS=LIVE")
print("TERMINAL_SUCCESS_PERSISTS_AFTER_DISCONNECT=YES")
print("RECOVERY_WINDOW_MINUTES=15")
print("DB=UNCHANGED")
print("AUTH=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
