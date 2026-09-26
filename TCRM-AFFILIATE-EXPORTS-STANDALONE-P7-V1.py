#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-AFFILIATE-EXPORTS-STANDALONE-P7-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
PAGE = ROOT / "client/src/pages/affiliate/ExportsPage.tsx"
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Download, FileSpreadsheet, FilterX, RefreshCw, Send } from "lucide-react";
import { toast } from "sonner";

const CRM_TAGS = ["DIRECT", "INS-MOHD", "ORG-MOHD", "CH-MKT", "IND-MKT"];

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

export default function ExportsPage() {
  const { user } = useAuth();
  const { isRTL } = useLanguage();
  const L = (ar: string, en: string) => (isRTL ? ar : en);
  const canExport = canManageRole(user?.role);

  const [month, setMonth] = useState(currentRiyadhMonth);
  const [filters, setFilters] = useState({
    courseId: "",
    tag: "",
    marketerCode: "",
    startDate: "",
    endDate: "",
  });

  const coursesQ = trpc.accountManagement.listCourseProducts.useQuery({});
  const reportQ = trpc.accountManagement.getEmaarCommissionReport.useQuery({ month });
  const invoicesQ = trpc.accountManagement.listEmaarCommissionInvoices.useQuery({ month });

  const courses = coursesQ.data ?? [];
  const report = reportQ.data ?? [];
  const invoices = invoicesQ.data ?? [];

  const totals = useMemo(() => ({
    reportRows: report.length,
    subscribers: report.reduce((sum: number, row: any) => sum + Number(row?.subscriberCount ?? 0), 0),
    commissions: report.reduce((sum: number, row: any) => sum + parseMoney(row?.totalCommission), 0),
    invoices: invoices.length,
  }), [report, invoices]);

  function resetFilters() {
    setFilters({ courseId: "", tag: "", marketerCode: "", startDate: "", endDate: "" });
  }

  function exportExcel() {
    if (!canExport) {
      toast.error(L("صلاحية المدير أو مدير المبيعات مطلوبة للتصدير", "Admin or Sales Manager permission is required to export"));
      return;
    }
    if (filters.startDate && filters.endDate && filters.startDate > filters.endDate) {
      toast.error(L("تاريخ البداية يجب أن يكون قبل تاريخ النهاية", "Start date must be before end date"));
      return;
    }

    const params = new URLSearchParams();
    if (month) params.set("month", month);
    if (filters.courseId) params.set("courseId", filters.courseId);
    if (filters.tag) params.set("tag", filters.tag);
    if (filters.marketerCode.trim()) params.set("marketerCode", filters.marketerCode.trim().toUpperCase());
    if (filters.startDate) params.set("startDate", filters.startDate);
    if (filters.endDate) params.set("endDate", filters.endDate);

    window.open(`/api/export/emaar-commissions?${params.toString()}`, "_blank", "noopener,noreferrer");
  }

  function refreshPreview() {
    void Promise.all([coursesQ.refetch(), reportQ.refetch(), invoicesQ.refetch()]);
  }

  return (
    <CRMLayout>
      <div className="space-y-5 p-4 md:p-6" dir={isRTL ? "rtl" : "ltr"}>
        <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-[#1e3a5f] to-[#6366f1] text-white shadow-lg">
              <Send className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-950">{L("التقارير والتصدير", "Reports & Export")}</h1>
              <p className="text-sm text-slate-500">
                {L("صدّر ملف Excel موحد للعمولات والفواتير والمسوقين والدورات مع فلاتر اختيارية.", "Export a unified Excel workbook for commissions, invoices, marketers and courses with optional filters.")}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-44" />
            <Button variant="outline" size="sm" onClick={refreshPreview} disabled={reportQ.isFetching || invoicesQ.isFetching}>
              <RefreshCw className={`h-4 w-4 ${reportQ.isFetching || invoicesQ.isFetching ? "animate-spin" : ""}`} />
              {L("تحديث", "Refresh")}
            </Button>
          </div>
        </div>

        {!canExport && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            {L("وضع عرض فقط: تنزيل ملف Excel متاح للمدير أو مدير المبيعات فقط.", "Read-only mode: Excel export is limited to Admin or Sales Manager.")}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4">
            <p className="text-xs font-bold text-blue-800">{L("صفوف تقرير العمولات", "Commission report rows")}</p>
            <p className="mt-1 text-2xl font-black text-blue-950">{totals.reportRows}</p>
          </div>
          <div className="rounded-2xl border border-cyan-100 bg-cyan-50 p-4">
            <p className="text-xs font-bold text-cyan-800">{L("المشتركين", "Subscribers")}</p>
            <p className="mt-1 text-2xl font-black text-cyan-950">{totals.subscribers}</p>
          </div>
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
            <p className="text-xs font-bold text-emerald-800">{L("إجمالي العمولات", "Total commissions")}</p>
            <p className="mt-1 text-2xl font-black text-emerald-950">{totals.commissions.toFixed(2)}</p>
          </div>
          <div className="rounded-2xl border border-violet-100 bg-violet-50 p-4">
            <p className="text-xs font-bold text-violet-800">{L("الفواتير", "Invoices")}</p>
            <p className="mt-1 text-2xl font-black text-violet-950">{totals.invoices}</p>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-black text-slate-950">{L("فلاتر التصدير", "Export filters")}</h2>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                {L("كل الفلاتر اختيارية. تركها فارغة يصدّر بيانات الشهر كاملة.", "All filters are optional. Leave them empty to export the full month.")}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={resetFilters}>
              <FilterX className="h-4 w-4" />
              {L("مسح الفلاتر", "Clear filters")}
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
            <Select
              value={filters.courseId || "__all__"}
              onValueChange={(value) => setFilters((s) => ({ ...s, courseId: value === "__all__" ? "" : value }))}
            >
              <SelectTrigger><SelectValue placeholder={L("كل الدورات", "All courses")} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">{L("كل الدورات", "All courses")}</SelectItem>
                {courses.map((course: any) => (
                  <SelectItem key={course.id} value={String(course.id)}>{course.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={filters.tag || "__all__"}
              onValueChange={(value) => setFilters((s) => ({ ...s, tag: value === "__all__" ? "" : value }))}
            >
              <SelectTrigger><SelectValue placeholder={L("كل الوسوم", "All tags")} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">{L("كل الوسوم", "All tags")}</SelectItem>
                {CRM_TAGS.map((tag) => <SelectItem key={tag} value={tag}>{tag}</SelectItem>)}
              </SelectContent>
            </Select>

            <Input
              placeholder={L("كود مسوق محدد", "Marketer code")}
              value={filters.marketerCode}
              onChange={(e) => setFilters((s) => ({ ...s, marketerCode: e.target.value.toUpperCase() }))}
            />

            <Input
              type="date"
              value={filters.startDate}
              onChange={(e) => setFilters((s) => ({ ...s, startDate: e.target.value }))}
            />

            <Input
              type="date"
              value={filters.endDate}
              onChange={(e) => setFilters((s) => ({ ...s, endDate: e.target.value }))}
            />
          </div>
        </div>

        <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="bg-gradient-to-l from-slate-950 via-[#1e3a5f] to-[#6366f1] px-5 py-4 text-white">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="h-5 w-5" />
              <div>
                <p className="text-sm font-black">{L("محتوى ملف Excel", "Excel workbook contents")}</p>
                <p className="text-[11px] text-white/75">
                  {L("ملخص شهري، تقرير العمولات، الفواتير، قائمة المسوقين، الدورات، وقالب فاتورة.", "Monthly summary, commission report, invoices, marketers, courses, and invoice template.")}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4 p-5">
            <div className="flex flex-wrap gap-2">
              {[
                L("الملخص الشهري", "Monthly summary"),
                L("تقرير العمولات", "Commission report"),
                L("الفواتير", "Invoices"),
                L("المسوقون", "Marketers"),
                L("الدورات", "Courses"),
                L("قالب فاتورة", "Invoice template"),
              ].map((item) => <Badge key={item} variant="outline" className="rounded-full px-3 py-1">{item}</Badge>)}
            </div>

            <Button
              onClick={exportExcel}
              disabled={!canExport}
              className="h-12 w-full rounded-2xl bg-gradient-to-r from-[#1e3a5f] to-[#6366f1] text-sm font-black text-white shadow-lg sm:w-auto sm:min-w-[230px]"
            >
              <Download className="h-4 w-4" />
              {L("تصدير Excel", "Export Excel")}
            </Button>
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
    changed.append("client/src/pages/affiliate/ExportsPage.tsx")

app = APP.read_text(encoding="utf-8")
app0 = app
if 'import ExportsPage from "./pages/affiliate/ExportsPage";' not in app:
    anchors = [
        'import MonthlyClosePage from "./pages/affiliate/MonthlyClosePage";',
        'import InvoicesPage from "./pages/affiliate/InvoicesPage";',
        'import CommissionsPage from "./pages/affiliate/CommissionsPage";',
        'import SubscriptionsPage from "./pages/affiliate/SubscriptionsPage";',
    ]
    for anchor in anchors:
        if anchor in app:
            app = app.replace(anchor, anchor + '\nimport ExportsPage from "./pages/affiliate/ExportsPage";', 1)
            break
    else:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=APP_IMPORT_ANCHOR_NOT_FOUND")
        sys.exit(2)

if '<Route path="/affiliate-marketing/exports" component={ExportsPage} />' not in app:
    route = '      <Route path="/affiliate-marketing/exports" component={ExportsPage} />\n'
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
layout = layout.replace('{ section: "exports",', '{ href: "/affiliate-marketing/exports",')
if layout.count('href: "/affiliate-marketing/exports"') < 2:
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=EXPORTS_SIDEBAR_GUARD_FAILED")
    sys.exit(4)
if 'const href = sub.href || `/clients?setup=1&section=${sub.section}`;' not in layout:
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=SIDEBAR_HREF_MAPPER_MISSING")
    sys.exit(5)
if layout != layout0:
    backup(LAYOUT)
    LAYOUT.write_text(layout, encoding="utf-8")
    changed.append("client/src/components/CRMLayout.tsx")

final_app = APP.read_text(encoding="utf-8")
if final_app.find('/affiliate-marketing/exports') > final_app.find('/affiliate-marketing/:tab'):
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=ROUTE_ORDER_INVALID")
    sys.exit(6)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + ";".join(changed))
print("ROUTE=/affiliate-marketing/exports")
print("EXPORT_ENDPOINT=/api/export/emaar-commissions")
print("FILTERS=month,courseId,tag,marketerCode,startDate,endDate")
print("LEGACY_CLIENTPOOL=UNCHANGED")
print("BACKEND_DB_AUTH=UNCHANGED")
print("BUILD_REQUIRED=YES")
print("COMMIT=NO")
print("PUSH=NO")
