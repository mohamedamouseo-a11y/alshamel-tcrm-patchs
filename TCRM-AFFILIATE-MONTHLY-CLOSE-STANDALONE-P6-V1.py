#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-AFFILIATE-MONTHLY-CLOSE-STANDALONE-P6-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
PAGE = ROOT / "client/src/pages/affiliate/MonthlyClosePage.tsx"
APP = ROOT / "client/src/App.tsx"
LAYOUT = ROOT / "client/src/components/CRMLayout.tsx"

for p in (APP, LAYOUT):
    if not p.exists():
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=MISSING:{p}")
        sys.exit(1)

PAGE_CONTENT = r'''import { useMemo, useState } from "react";
import CRMLayout from "@/components/CRMLayout";
import { trpc } from "@/lib/trpc";
import { useAuth } from "@/_core/hooks/useAuth";
import { useLanguage } from "@/contexts/LanguageContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Calendar, CheckCircle2, Lock, RefreshCw, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

function normalizeRole(role: unknown): string {
  const compact = String(role ?? "").trim().replace(/[\s_-]+/g, "").toLowerCase();
  if (compact === "admin") return "Admin";
  if (compact === "salesmanager") return "SalesManager";
  return String(role ?? "").trim();
}

function canManageRole(role: unknown): boolean {
  return ["Admin", "SalesManager"].includes(normalizeRole(role));
}

function currentRiyadhMonth(): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Riyadh",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(new Date());
  const year = parts.find((p) => p.type === "year")?.value ?? String(new Date().getFullYear());
  const month = parts.find((p) => p.type === "month")?.value ?? String(new Date().getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

function parseMoney(value: unknown): number {
  const n = Number(String(value ?? "0").replace(/,/g, "").replace(/[^0-9.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function getClosedSummary(value: any): any {
  if (!value) return null;
  if (typeof value === "string") {
    try { return JSON.parse(value); } catch { return null; }
  }
  return value;
}

export default function MonthlyClosePage() {
  const { user } = useAuth();
  const { isRTL } = useLanguage();
  const L = (ar: string, en: string) => (isRTL ? ar : en);
  const canManage = canManageRole(user?.role);
  const [month, setMonth] = useState(currentRiyadhMonth);

  const kpisQ = trpc.accountManagement.getEmaarDashboardKpis.useQuery({ month });
  const reportQ = trpc.accountManagement.getEmaarCommissionReport.useQuery({ month });
  const invoicesQ = trpc.accountManagement.listEmaarCommissionInvoices.useQuery({ month });
  const closedMonthsQ = trpc.accountManagement.listEmaarClosedMonths.useQuery();

  const closedMonths = closedMonthsQ.data ?? [];
  const closedMonth = closedMonths.find((item: any) => item.periodMonth === month);
  const isClosed = Boolean(closedMonth);
  const closedSummary = getClosedSummary((closedMonth as any)?.summaryJson);

  const liveKpis = kpisQ.data as any;
  const liveReport = reportQ.data ?? [];
  const liveInvoices = invoicesQ.data ?? [];

  const visibleKpis = isClosed ? (closedSummary?.kpis ?? liveKpis) : liveKpis;
  const visibleReport = isClosed ? (closedSummary?.report ?? liveReport) : liveReport;
  const visibleInvoices = isClosed ? (closedSummary?.invoices ?? liveInvoices) : liveInvoices;

  const totals = useMemo(() => {
    const subscribers = visibleReport.reduce((sum: number, row: any) => sum + Number(row?.subscriberCount ?? 0), 0);
    const commissions = visibleReport.reduce((sum: number, row: any) => sum + parseMoney(row?.totalCommission), 0);
    const paidInvoices = visibleInvoices.filter((inv: any) => inv.status === "Paid").length;
    const openInvoices = visibleInvoices.filter((inv: any) => inv.status !== "Paid").length;
    return { subscribers, commissions, paidInvoices, openInvoices };
  }, [visibleReport, visibleInvoices]);

  const closeM = trpc.accountManagement.closeEmaarCommissionMonth.useMutation({
    onSuccess: async (result) => {
      await Promise.all([
        closedMonthsQ.refetch(),
        kpisQ.refetch(),
        reportQ.refetch(),
        invoicesQ.refetch(),
      ]);
      toast.success(L(`تم إغلاق شهر ${result.periodMonth}`, `Closed month ${result.periodMonth}`));
    },
    onError: (error) => toast.error(error.message),
  });

  const loading = kpisQ.isLoading || reportQ.isLoading || invoicesQ.isLoading || closedMonthsQ.isLoading;

  function refreshAll() {
    void Promise.all([
      kpisQ.refetch(),
      reportQ.refetch(),
      invoicesQ.refetch(),
      closedMonthsQ.refetch(),
    ]);
  }

  return (
    <CRMLayout>
      <div className="space-y-5 p-4 md:p-6" dir={isRTL ? "rtl" : "ltr"}>
        <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-[#0f766e] to-[#14b8a6] text-white shadow-lg">
              <Calendar className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-950">{L("الإغلاق الشهري", "Monthly Close")}</h1>
              <p className="text-sm text-slate-500">{L("راجع أرقام الشهر ثم أنشئ Snapshot مختوم يحمي العمولات والفواتير من التغيير.", "Review the month, then create a sealed snapshot that protects commissions and invoices from changes.")}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {isClosed ? (
              <Badge className="gap-1 rounded-full bg-emerald-100 text-emerald-800 hover:bg-emerald-100">
                <CheckCircle2 className="h-3.5 w-3.5" /> {L("مغلق", "Closed")}
              </Badge>
            ) : (
              <Badge variant="outline" className="gap-1 rounded-full border-blue-200 bg-blue-50 text-blue-800">
                <ShieldCheck className="h-3.5 w-3.5" /> {L("مفتوح", "Open")}
              </Badge>
            )}
            <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-44" />
            <Button variant="outline" size="sm" onClick={refreshAll} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              {L("تحديث", "Refresh")}
            </Button>
          </div>
        </div>

        {!canManage && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            {L("وضع عرض فقط: إغلاق الشهر متاح للمدير أو مدير المبيعات فقط.", "Read-only mode: closing a month is limited to Admin or Sales Manager.")}
          </div>
        )}

        {isClosed && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
            <div className="flex items-start gap-2">
              <Lock className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-bold">{L(`شهر ${month} مغلق ومحمي`, `Month ${month} is closed and sealed`)}</p>
                <p className="mt-1 text-xs">
                  {L("البيانات المعروضة من Snapshot الإغلاق وليست من بيانات قابلة للتعديل.", "Displayed values come from the closing snapshot, not mutable live data.")}
                  {(closedMonth as any)?.closedAt ? ` · ${String((closedMonth as any).closedAt)}` : ""}
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4"><p className="text-xs font-bold text-blue-800">{L("مشتركين جدد", "New subscribers")}</p><p className="mt-1 text-2xl font-black text-blue-950">{visibleKpis?.newSubscribers ?? totals.subscribers}</p></div>
          <div className="rounded-2xl border border-violet-100 bg-violet-50 p-4"><p className="text-xs font-bold text-violet-800">{L("أفضل مسوق", "Top marketer")}</p><p className="mt-1 text-lg font-black text-violet-950">{visibleKpis?.topMarketer?.marketerCode ?? "—"}</p><p className="text-[11px] text-violet-700">{visibleKpis?.topMarketer?.marketerName ?? ""}</p></div>
          <div className="rounded-2xl border border-cyan-100 bg-cyan-50 p-4"><p className="text-xs font-bold text-cyan-800">{L("أكثر دورة طلبًا", "Top course")}</p><p className="mt-1 text-lg font-black text-cyan-950">{visibleKpis?.topCourse?.courseName ?? "—"}</p></div>
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4"><p className="text-xs font-bold text-emerald-800">{L("إجمالي العمولات", "Total commissions")}</p><p className="mt-1 text-2xl font-black text-emerald-950">{totals.commissions.toFixed(2)}</p></div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><p className="text-xs font-bold text-slate-700">{L("فواتير مفتوحة", "Open invoices")}</p><p className="mt-1 text-2xl font-black text-slate-900">{totals.openInvoices}</p><p className="text-[11px] text-slate-500">{totals.paidInvoices} {L("مدفوعة", "paid")}</p></div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-base font-black text-slate-950">{L("تثبيت أرقام الشهر", "Seal monthly figures")}</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
                {L("عند الإغلاق سيتم حفظ Snapshot مختوم للتقرير والفواتير. بعد ذلك لن يمكن تعديل اشتراك أو فاتورة تؤثر على هذا الشهر.", "Closing stores a sealed snapshot of the report and invoices. After that, subscriptions or invoices affecting this month cannot be modified.")}
              </p>
            </div>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  disabled={!canManage || isClosed || closeM.isPending || loading}
                  className="min-w-[170px] rounded-2xl bg-gradient-to-r from-[#0f766e] to-[#14b8a6] font-black text-white shadow-lg"
                >
                  <Lock className="h-4 w-4" />
                  {isClosed ? L("الشهر مغلق", "Month closed") : L("إغلاق الشهر", "Close month")}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent dir={isRTL ? "rtl" : "ltr"}>
                <AlertDialogHeader>
                  <AlertDialogTitle>{L(`تأكيد إغلاق شهر ${month}`, `Confirm closing ${month}`)}</AlertDialogTitle>
                  <AlertDialogDescription>
                    {L("سيتم إنشاء Snapshot مختوم للتقرير والفواتير. هذا الإجراء يقفل الشهر محاسبيًا.", "A sealed snapshot of the report and invoices will be created. This locks the month for accounting.")}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <div className="grid grid-cols-2 gap-2 rounded-2xl bg-slate-50 p-3 text-xs">
                  <div><span className="text-slate-500">{L("المشتركين", "Subscribers")}</span><p className="font-black">{totals.subscribers}</p></div>
                  <div><span className="text-slate-500">{L("العمولات", "Commissions")}</span><p className="font-black">{totals.commissions.toFixed(2)}</p></div>
                  <div><span className="text-slate-500">{L("الفواتير", "Invoices")}</span><p className="font-black">{visibleInvoices.length}</p></div>
                  <div><span className="text-slate-500">{L("المفتوحة", "Open")}</span><p className="font-black">{totals.openInvoices}</p></div>
                </div>
                <AlertDialogFooter>
                  <AlertDialogCancel>{L("إلغاء", "Cancel")}</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => closeM.mutate({ periodMonth: month, notes: "إغلاق شهري من صفحة Affiliate Marketing المستقلة" })}
                  >
                    {L("تأكيد الإغلاق", "Confirm close")}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="bg-gradient-to-l from-slate-950 via-[#1e3a5f] to-[#0f766e] px-4 py-3 text-white">
            <p className="text-sm font-black">{L("سجل الشهور المغلقة", "Closed months history")}</p>
            <p className="text-[11px] text-white/75">{L("مرجع سريع للشهور التي تم تثبيت أرقامها.", "Quick reference for months whose figures were sealed.")}</p>
          </div>
          <div className="divide-y divide-slate-100">
            {closedMonths.map((item: any) => {
              const summary = getClosedSummary(item.summaryJson);
              const report = summary?.report ?? [];
              const invoices = summary?.invoices ?? [];
              const commissions = report.reduce((sum: number, row: any) => sum + parseMoney(row?.totalCommission), 0);
              return (
                <div key={item.id ?? item.periodMonth} className="grid grid-cols-1 gap-2 px-4 py-3 text-xs md:grid-cols-[1fr_1.3fr_.8fr_.8fr] md:items-center">
                  <div><p className="text-[10px] font-bold text-slate-400">{L("الشهر", "Month")}</p><p className="font-black text-slate-900">{item.periodMonth}</p></div>
                  <div><p className="text-[10px] font-bold text-slate-400">{L("تاريخ الإغلاق", "Closed at")}</p><p className="text-slate-700">{item.closedAt ?? "—"}</p></div>
                  <div><p className="text-[10px] font-bold text-slate-400">{L("الفواتير", "Invoices")}</p><p className="font-black">{invoices.length}</p></div>
                  <div><p className="text-[10px] font-bold text-slate-400">{L("العمولات", "Commissions")}</p><p className="font-black text-emerald-700">{commissions.toFixed(2)}</p></div>
                </div>
              );
            })}
            {!closedMonthsQ.isLoading && closedMonths.length === 0 && (
              <p className="p-4 text-sm text-slate-500">{L("لا توجد شهور مغلقة بعد.", "No closed months yet.")}</p>
            )}
          </div>
        </div>
      </div>
    </CRMLayout>
  );
}
'''

def backup(path: Path):
    if not path.exists():
        return None
    b = Path("/tmp") / f"{path.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(path, b)
    return b

changed = []

PAGE.parent.mkdir(parents=True, exist_ok=True)
if not PAGE.exists() or PAGE.read_text(encoding="utf-8") != PAGE_CONTENT:
    backup(PAGE)
    PAGE.write_text(PAGE_CONTENT, encoding="utf-8")
    changed.append("client/src/pages/affiliate/MonthlyClosePage.tsx")

app = APP.read_text(encoding="utf-8")
app0 = app
if 'import MonthlyClosePage from "./pages/affiliate/MonthlyClosePage";' not in app:
    anchors = [
        'import InvoicesPage from "./pages/affiliate/InvoicesPage";',
        'import CommissionsPage from "./pages/affiliate/CommissionsPage";',
        'import SubscriptionsPage from "./pages/affiliate/SubscriptionsPage";',
        'import CoursesPage from "./pages/affiliate/CoursesPage";',
    ]
    for anchor in anchors:
        if anchor in app:
            app = app.replace(anchor, anchor + '\nimport MonthlyClosePage from "./pages/affiliate/MonthlyClosePage";', 1)
            break
    else:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=APP_IMPORT_ANCHOR_NOT_FOUND")
        sys.exit(2)

if '<Route path="/affiliate-marketing/monthly-close" component={MonthlyClosePage} />' not in app:
    route = '      <Route path="/affiliate-marketing/monthly-close" component={MonthlyClosePage} />\n'
    generic = '<Route path="/affiliate-marketing" component={BDAdvancedSettings} />'
    if generic in app:
        app = app.replace(generic, route + generic, 1)
    else:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=APP_ROUTE_ANCHOR_NOT_FOUND")
        sys.exit(3)

if app != app0:
    backup(APP)
    APP.write_text(app, encoding="utf-8")
    changed.append("client/src/App.tsx")

layout = LAYOUT.read_text(encoding="utf-8")
layout0 = layout
layout = layout.replace('{ section: "monthly-close",', '{ href: "/affiliate-marketing/monthly-close",')
if layout.count('href: "/affiliate-marketing/monthly-close"') < 2:
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=MONTHLY_CLOSE_SIDEBAR_GUARD_FAILED")
    sys.exit(4)
if 'const href = sub.href || `/clients?setup=1&section=${sub.section}`;' not in layout:
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=SIDEBAR_HREF_MAPPER_MISSING")
    sys.exit(5)
if layout != layout0:
    backup(LAYOUT)
    LAYOUT.write_text(layout, encoding="utf-8")
    changed.append("client/src/components/CRMLayout.tsx")

final_app = APP.read_text(encoding="utf-8")
if final_app.find('/affiliate-marketing/monthly-close') > final_app.find('/affiliate-marketing/:tab'):
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=ROUTE_ORDER_INVALID")
    sys.exit(6)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + ";".join(changed))
print("ROUTE=/affiliate-marketing/monthly-close")
print("CLOSE_MUTATION=closeEmaarCommissionMonth")
print("CLOSED_SNAPSHOT=SUPPORTED")
print("LEGACY_CLIENTPOOL=UNCHANGED")
print("BACKEND_DB_AUTH=UNCHANGED")
print("BUILD_REQUIRED=YES")
print("COMMIT=NO")
print("PUSH=NO")
