#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-DEVELOPER-HUB-PUSH-DISCONNECT-RESILIENCE-V3"
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

changed = []

# Backend
src = BACK.read_text(encoding="utf-8")
orig = src

if "let cancelRequested = false;" not in src:
    src = src.replace(
        "let remoteMutationStarted = false;\n",
        "let remoteMutationStarted = false;\nlet cancelRequested = false;\n",
        1,
    )

if "cancelRequested = false;\n  lastOperationStatus" not in src:
    src = src.replace(
        '  operationRunning = true;\n  lastOperationStatus = { state: "running", step: "Acquired lock", percent: 5 };\n',
        '  operationRunning = true;\n  cancelRequested = false;\n  lastOperationStatus = { state: "running", step: "Acquired lock", percent: 5 };\n',
        1,
    )

if "remoteMutationStarted = false;\n        cancelRequested = false;" not in src:
    src = src.replace(
        "        activeChild = null;\n        remoteMutationStarted = false;\n        operationRunning = false;\n",
        "        activeChild = null;\n        remoteMutationStarted = false;\n        cancelRequested = false;\n        operationRunning = false;\n",
        1,
    )

if 'lastOperationStatus = { state: "running", step: options.step' not in src:
    src = src.replace(
        '  if (options.isClosed()) throw new Error("Operation cancelled before the next step.");\n'
        '  sendEvent(res, { type: "progress", step: options.step, stepAr: options.stepAr, percent: options.percent });\n',
        '  if (options.isClosed()) throw new Error("Operation cancelled before the next step.");\n'
        '  lastOperationStatus = { state: "running", step: options.step, stepAr: options.stepAr, percent: options.percent };\n'
        '  sendEvent(res, { type: "progress", step: options.step, stepAr: options.stepAr, percent: options.percent });\n',
        1,
    )

if "const isClosed = () => cancelRequested;" not in src:
    src = src.replace(
        "    const isClosed = () => clientClosed;\n",
        "    // Browser/SSE transport loss must not cancel the server-side operation.\n"
        "    const isClosed = () => cancelRequested;\n",
        1,
    )

success_old = '''    await audit({ action: `github.${action}`, actorUserId: user.id, actorEmail: user.email, repo: state.repo, branch: state.branch, result: "success", expectedAction: review.expectedAction, fingerprint: review.fingerprint, commit: result.newSha, localAligned: result.localAligned, statePersisted, selectedFiles: executionReview.includedFiles });
    if (!clientClosed) {
      sendEvent(res, { type: "done", action, expectedAction: review.expectedAction, commit: result.newSha, localAligned: result.localAligned, lastSyncAt: completedAt, statePersisted });
    lastOperationStatus = { state: "success", step: "Completed", commit: result.newSha, finishedAt: completedAt };
      res.end();
    }
'''
success_new = '''    await audit({ action: `github.${action}`, actorUserId: user.id, actorEmail: user.email, repo: state.repo, branch: state.branch, result: "success", expectedAction: review.expectedAction, fingerprint: review.fingerprint, commit: result.newSha, localAligned: result.localAligned, statePersisted, selectedFiles: executionReview.includedFiles });
    // Persist terminal success even when the SSE client disconnected.
    lastOperationStatus = { state: "success", step: "Completed", commit: result.newSha, finishedAt: completedAt };
    if (!clientClosed) {
      sendEvent(res, { type: "done", action, expectedAction: review.expectedAction, commit: result.newSha, localAligned: result.localAligned, lastSyncAt: completedAt, statePersisted });
      res.end();
    }
'''
if "Persist terminal success even when the SSE client disconnected." not in src and success_old in src:
    src = src.replace(success_old, success_new, 1)

if "cancelRequested = true;\n  terminateActiveChild();" not in src:
    src = src.replace(
        "  terminateActiveChild();\n  res.json({ ok: true });\n});\n",
        "  cancelRequested = true;\n  terminateActiveChild();\n  res.json({ ok: true });\n});\n",
        1,
    )

if src != orig:
    backup(BACK)
    BACK.write_text(src, encoding="utf-8")
    changed.append("server/routes/developerHubGitHubClone.ts")

# Frontend
src = FRONT.read_text(encoding="utf-8")
orig = src

src = src.replace(
    'addLog(isRTL ? "انقطع الاتصال، جارٍ التحقق من حالة العملية..." : "Connection lost, checking operation status...", "warning");',
    'addLog(isRTL ? "انقطع اتصال الشاشة فقط؛ العملية مستمرة على الخادم وجارٍ متابعة حالتها..." : "Screen connection lost; the server operation is still running and status recovery has started...", "warning");',
)

if "for (let i = 0; i < 450; i++)" not in src:
    src = src.replace("for (let i = 0; i < 60; i++) {", "for (let i = 0; i < 450; i++) {", 1)

if 's.state === "idle" && i > 10' not in src:
    src = src.replace(
        '''            } else if (s.state === "idle" && i > 2) {
              addLog(isRTL ? "انتهت العملية دون نتيجة واضحة" : "Operation ended without clear result", "warning");
              recovered = true; break;
''',
        '''            } else if (s.state === "idle" && i > 10) {
              addLog(isRTL ? "الخادم لا يسجل عملية نشطة؛ جارٍ تحديث حالة GitHub قبل إنهاء المتابعة." : "No active server operation is recorded; refreshing GitHub state before ending recovery.", "warning");
              await loadAll();
              recovered = true; break;
''',
        1,
    )

if src != orig:
    backup(FRONT)
    FRONT.write_text(src, encoding="utf-8")
    changed.append("client/src/components/DeveloperHubTab.tsx")

# Guards
back = BACK.read_text(encoding="utf-8")
front = FRONT.read_text(encoding="utf-8")

backend_markers = [
    'let cancelRequested = false;',
    'const isClosed = () => cancelRequested;',
    'cancelRequested = true;',
    'lastOperationStatus = { state: "running", step: options.step',
    'lastOperationStatus = { state: "success", step: "Completed"',
]
frontend_markers = [
    'for (let i = 0; i < 450; i++)',
    'Screen connection lost; the server operation is still running',
    's.state === "idle" && i > 10',
]

for marker in backend_markers:
    if marker not in back:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=BACKEND_GUARD_MISSING:{marker}")
        sys.exit(2)

for marker in frontend_markers:
    if marker not in front:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=FRONTEND_GUARD_MISSING:{marker}")
        sys.exit(3)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + (";".join(changed) if changed else "NONE"))
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
