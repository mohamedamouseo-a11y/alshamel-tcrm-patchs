#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-AFFILIATE-P1-P3-CRM-LAYOUT-RECOVERY-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
AFF = ROOT / "client/src/pages/affiliate"
MARKETERS = AFF / "MarketersPage.tsx"
COURSES = AFF / "CoursesPage.tsx"
SUBSCRIPTIONS = AFF / "SubscriptionsPage.tsx"

for p in (MARKETERS, COURSES, SUBSCRIPTIONS):
    if not p.exists():
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=MISSING:{p}")
        sys.exit(1)

def backup(path: Path):
    b = Path("/tmp") / f"{path.name}.{PATCH}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(path, b)
    return b

def ensure_crm_layout(path: Path):
    src = path.read_text(encoding="utf-8")
    if "<CRMLayout" in src and 'from "@/components/CRMLayout"' in src:
        return False

    original = src
    if 'from "@/components/CRMLayout"' not in src:
        first_import_end = src.find("\n")
        if first_import_end < 0:
            raise RuntimeError(f"IMPORT_ANCHOR_MISSING:{path.name}")
        src = src[:first_import_end+1] + 'import CRMLayout from "@/components/CRMLayout";\n' + src[first_import_end+1:]

    markers = [
        '<div className="space-y-6 p-6">',
        '<div className="space-y-6 p-6" dir="rtl">',
    ]
    root = next((m for m in markers if m in src), None)
    if not root:
        raise RuntimeError(f"ROOT_MARKER_MISSING:{path.name}")

    src = src.replace("return (\n" + root, "return (\n<CRMLayout>\n" + root, 1)

    end_markers = ["\n</div>\n);\n}", "\n    </div>\n  );\n}"]
    replaced = False
    for end in end_markers:
        if src.endswith(end):
            if end.startswith("\n    "):
                src = src[:-len(end)] + "\n    </div>\n    </CRMLayout>\n  );\n}"
            else:
                src = src[:-len(end)] + "\n</div>\n</CRMLayout>\n);\n}"
            replaced = True
            break
    if not replaced:
        idx = src.rfind("</div>")
        if idx < 0:
            raise RuntimeError(f"CLOSING_ROOT_MISSING:{path.name}")
        src = src[:idx+6] + "\n</CRMLayout>" + src[idx+6:]

    if src == original:
        return False

    backup(path)
    path.write_text(src, encoding="utf-8")
    return True

SUBSCRIPTIONS_CONTENT = r'''import { useMemo, useState } from "react";
import CRMLayout from "@/components/CRMLayout";
import { trpc } from "@/lib/trpc";
import { useLanguage } from "@/contexts/LanguageContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { BookOpen, ClipboardList, RefreshCw, Search, UserPlus, WalletCards } from "lucide-react";
import { toast } from "sonner";

const CRM_TAGS = ["DIRECT", "INS-MOHD", "ORG-MOHD", "CH-MKT", "IND-MKT"];

function getTodayRiyadh(): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Riyadh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const y = parts.find((p) => p.type === "year")?.value ?? "";
  const m = parts.find((p) => p.type === "month")?.value ?? "";
  const d = parts.find((p) => p.type === "day")?.value ?? "";
  return `${y}-${m}-${d}`;
}

function entityTag(course?: any): string | null {
  if (course?.organizingEntity === "GoldenEmaar") return "ORG-MOHD";
  if (course?.organizingEntity === "InstituteEmaar") return "INS-MOHD";
  return null;
}

function allowedTags(sourceCode: string, marketers: any[], course?: any): string[] {
  const code = String(sourceCode ?? "").trim().toUpperCase();
  if (code && code !== "DIRECT") {
    const marketer = marketers.find((m: any) => String(m.code).toUpperCase() === code);
    if (marketer?.type === "Channel") return ["CH-MKT"];
    if (marketer?.type === "Individual") return ["IND-MKT"];
    if (marketer?.type === "Institute") return ["INS-MOHD"];
  }
  const tag = entityTag(course);
  return tag && tag !== "DIRECT" ? ["DIRECT", tag] : ["DIRECT"];
}

export default function SubscriptionsPage() {
  const { isRTL } = useLanguage();
  const L = (ar: string, en: string) => (isRTL ? ar : en);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({
    leadName: "",
    phone: "",
    businessProfile: "",
    courseId: "",
    marketerCode: "",
    secondaryMarketerCode: "",
    primaryMarketerRatio: "100",
    secondaryMarketerRatio: "0",
    crmTag: "DIRECT",
    registrationDate: getTodayRiyadh(),
    paymentStatus: "Paid",
    paidAmount: "",
    notes: "",
  });

  const clientsQ = trpc.accountManagement.listClients.useQuery({
    search: search || undefined,
    limit: 100,
    offset: 0,
  });
  const coursesQ = trpc.accountManagement.listCourseProducts.useQuery({});
  const marketersQ = trpc.accountManagement.listMarketers.useQuery({ isActive: true });

  const clients = clientsQ.data?.data ?? [];
  const courses = coursesQ.data ?? [];
  const marketers = marketersQ.data ?? [];
  const activeCourses = courses.filter((c: any) => c.isActive !== 0);

  const selectedCourse = courses.find((c: any) => String(c.id) === String(form.courseId));
  const validTags = allowedTags(form.marketerCode, marketers, selectedCourse);

  const subscriptionClients = useMemo(
    () => clients.filter((client: any) =>
      client.primaryCourseName ||
      client.primaryMarketerCode ||
      client.primaryPaymentStatus ||
      client.primaryCrmTag
    ),
    [clients],
  );

  const createM = trpc.accountManagement.createClientWithCourseSubscription.useMutation({
    onSuccess: async (result) => {
      await clientsQ.refetch();
      setForm({
        leadName: "",
        phone: "",
        businessProfile: "",
        courseId: "",
        marketerCode: "",
        secondaryMarketerCode: "",
        primaryMarketerRatio: "100",
        secondaryMarketerRatio: "0",
        crmTag: "DIRECT",
        registrationDate: getTodayRiyadh(),
        paymentStatus: "Paid",
        paidAmount: "",
        notes: "",
      });
      toast.success(
        result.reusedExistingClient
          ? L("تمت إضافة دورة جديدة لعميل موجود", "Added course to existing client")
          : L("تم إنشاء العميل والاشتراك بنجاح", "Client and subscription created"),
      );
    },
    onError: (error) => toast.error(error.message),
  });

  function updateSource(value: string) {
    const marketerCode = value === "__none__" ? "" : value;
    const tags = allowedTags(marketerCode, marketers, selectedCourse);
    setForm((s) => ({ ...s, marketerCode, crmTag: tags[0] }));
  }

  function updateCourse(value: string) {
    const courseId = value === "__none__" ? "" : value;
    const course = courses.find((c: any) => String(c.id) === String(courseId));
    const tags = allowedTags(form.marketerCode, marketers, course);
    setForm((s) => ({ ...s, courseId, crmTag: tags[0] }));
  }

  async function submit() {
    if (!form.leadName.trim()) return toast.error(L("اسم العميل مطلوب", "Client name is required"));
    if (!form.phone.trim()) return toast.error(L("رقم الجوال مطلوب", "Phone is required"));
    if (!form.businessProfile.trim()) return toast.error(L("النشاط / وصف العميل مطلوب", "Business profile is required"));
    if (!form.courseId) return toast.error(L("الدورة مطلوبة", "Course is required"));
    if (!form.marketerCode) return toast.error(L("المصدر / كود المسوق مطلوب", "Source / marketer is required"));
    if (!form.registrationDate) return toast.error(L("تاريخ التسجيل مطلوب", "Registration date is required"));

    const paid = Number(String(form.paidAmount || "0").replace(",", "."));
    if ((form.paymentStatus === "Paid" || form.paymentStatus === "PartiallyPaid") && (!Number.isFinite(paid) || paid <= 0)) {
      return toast.error(L("المبلغ المدفوع يجب أن يكون أكبر من صفر", "Paid amount must be greater than zero"));
    }

    if (form.secondaryMarketerCode) {
      const totalRatio = Number(form.primaryMarketerRatio || 0) + Number(form.secondaryMarketerRatio || 0);
      if (Math.abs(totalRatio - 100) > 0.01) {
        return toast.error(L("نسب المسوقين يجب أن تساوي 100%", "Marketer ratios must equal 100%"));
      }
    }

    const source = form.marketerCode.trim().toUpperCase();
    await createM.mutateAsync({
      client: {
        businessProfile: form.businessProfile.trim(),
        leadName: form.leadName.trim(),
        phone: form.phone.trim(),
        planStatus: "Active" as any,
        renewalStatus: "Pending" as any,
        sourceMarketerCode: source,
        crmTag: form.crmTag as any,
        registrationDate: form.registrationDate,
        paymentStatus: form.paymentStatus as any,
        paidAmount: form.paidAmount || "0",
      },
      subscription: {
        courseId: Number(form.courseId),
        marketerCode: source,
        secondaryMarketerCode: form.secondaryMarketerCode || undefined,
        primaryMarketerRatio: form.primaryMarketerRatio || undefined,
        secondaryMarketerRatio: form.secondaryMarketerRatio || undefined,
        tag: form.crmTag as any,
        registrationDate: form.registrationDate,
        paymentStatus: form.paymentStatus as any,
        paidAmount: form.paidAmount || "0",
        notes: form.notes.trim() || undefined,
      },
    });
  }

  return (
    <CRMLayout>
      <div className="space-y-6 p-4 md:p-6" dir={isRTL ? "rtl" : "ltr"}>
        <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-[#0891b2] to-[#6366f1] text-white shadow-lg">
              <ClipboardList className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-950">{L("الاشتراكات والدفع", "Subscriptions & Payments")}</h1>
              <p className="text-sm text-slate-500">{L("إضافة اشتراك دورة وربطه بالمسوق وحالة الدفع.", "Add course subscriptions with marketer and payment details.")}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={() => clientsQ.refetch()} disabled={clientsQ.isFetching}>
            <RefreshCw className={`h-4 w-4 ${clientsQ.isFetching ? "animate-spin" : ""}`} />
            {L("تحديث", "Refresh")}
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[430px_1fr]">
          <div className="space-y-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
              <UserPlus className="h-5 w-5 text-indigo-600" />
              <h2 className="font-black text-slate-900">{L("إضافة اشتراك", "Add subscription")}</h2>
            </div>

            <Input value={form.leadName} onChange={(e) => setForm((s) => ({ ...s, leadName: e.target.value }))} placeholder={L("اسم العميل", "Client name")} />
            <Input value={form.phone} onChange={(e) => setForm((s) => ({ ...s, phone: e.target.value }))} placeholder={L("رقم الجوال", "Phone")} dir="ltr" />
            <Input value={form.businessProfile} onChange={(e) => setForm((s) => ({ ...s, businessProfile: e.target.value }))} placeholder={L("النشاط / وصف العميل", "Business profile")} />

            <Select value={form.courseId || "__none__"} onValueChange={updateCourse}>
              <SelectTrigger><SelectValue placeholder={L("اختر الدورة", "Select course")} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">{L("— اختر الدورة —", "— Select course —")}</SelectItem>
                {activeCourses.map((course: any) => <SelectItem key={course.id} value={String(course.id)}>{course.name} · {course.status}</SelectItem>)}
              </SelectContent>
            </Select>

            <Select value={form.marketerCode || "__none__"} onValueChange={updateSource}>
              <SelectTrigger><SelectValue placeholder={L("المصدر / كود المسوق", "Source / marketer")} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">{L("— اختر المصدر —", "— Select source —")}</SelectItem>
                <SelectItem value="DIRECT">{L("DIRECT · عميل مباشر", "DIRECT · Direct")}</SelectItem>
                {marketers.map((m: any) => <SelectItem key={m.id} value={m.code}>{m.code} · {m.name}</SelectItem>)}
              </SelectContent>
            </Select>

            <Select value={form.secondaryMarketerCode || "__none__"} onValueChange={(v) => setForm((s) => ({
              ...s,
              secondaryMarketerCode: v === "__none__" ? "" : v,
              primaryMarketerRatio: v === "__none__" ? "100" : (s.primaryMarketerRatio || "50"),
              secondaryMarketerRatio: v === "__none__" ? "0" : (s.secondaryMarketerRatio || "50"),
            }))}>
              <SelectTrigger><SelectValue placeholder={L("مسوق ثانٍ اختياري", "Optional secondary marketer")} /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">{L("— بدون —", "— None —")}</SelectItem>
                {marketers.filter((m: any) => m.code !== form.marketerCode).map((m: any) => <SelectItem key={m.id} value={m.code}>{m.code} · {m.name}</SelectItem>)}
              </SelectContent>
            </Select>

            {form.secondaryMarketerCode && (
              <div className="grid grid-cols-2 gap-2">
                <Input value={form.primaryMarketerRatio} onChange={(e) => setForm((s) => ({ ...s, primaryMarketerRatio: e.target.value }))} placeholder="50" inputMode="decimal" />
                <Input value={form.secondaryMarketerRatio} onChange={(e) => setForm((s) => ({ ...s, secondaryMarketerRatio: e.target.value }))} placeholder="50" inputMode="decimal" />
              </div>
            )}

            <Select value={form.crmTag} onValueChange={(v) => setForm((s) => ({ ...s, crmTag: v }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {CRM_TAGS.filter((tag) => validTags.includes(tag)).map((tag) => <SelectItem key={tag} value={tag}>{tag}</SelectItem>)}
              </SelectContent>
            </Select>

            <Input type="date" value={form.registrationDate} onChange={(e) => setForm((s) => ({ ...s, registrationDate: e.target.value }))} />

            <Select value={form.paymentStatus} onValueChange={(v) => setForm((s) => ({ ...s, paymentStatus: v }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Paid">{L("مدفوع", "Paid")}</SelectItem>
                <SelectItem value="PartiallyPaid">{L("مدفوع جزئيًا", "Partially Paid")}</SelectItem>
                <SelectItem value="Unpaid">{L("لم يدفع", "Unpaid")}</SelectItem>
              </SelectContent>
            </Select>

            <Input value={form.paidAmount} onChange={(e) => setForm((s) => ({ ...s, paidAmount: e.target.value }))} placeholder={L("المبلغ المدفوع", "Paid amount")} inputMode="decimal" />
            <Textarea value={form.notes} onChange={(e) => setForm((s) => ({ ...s, notes: e.target.value }))} placeholder={L("ملاحظات الاشتراك", "Subscription notes")} rows={3} />

            <Button onClick={submit} disabled={createM.isPending} className="h-11 w-full rounded-2xl bg-gradient-to-r from-[#0891b2] to-[#6366f1] font-black text-white">
              {createM.isPending ? L("جاري الحفظ...", "Saving...") : L("حفظ الاشتراك", "Save subscription")}
            </Button>
          </div>

          <div className="space-y-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-black text-slate-900">{L("الاشتراكات الحالية", "Current subscriptions")}</h2>
                <p className="text-xs text-slate-500">{subscriptionClients.length} {L("عميل مرتبط بدورة/دفع", "clients with course/payment data")}</p>
              </div>
              <div className="relative w-full sm:w-72">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={L("بحث...", "Search...")} className="pl-9" />
              </div>
            </div>

            {clientsQ.isLoading ? (
              <div className="py-12 text-center text-sm text-slate-500">{L("جاري التحميل...", "Loading...")}</div>
            ) : subscriptionClients.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-500">
                {L("لا توجد اشتراكات مطابقة.", "No matching subscriptions.")}
              </div>
            ) : (
              <div className="space-y-2">
                {subscriptionClients.map((client: any) => (
                  <div key={client.id} className="grid grid-cols-1 gap-3 rounded-2xl border border-slate-100 bg-slate-50/70 p-4 md:grid-cols-[1.4fr_1.4fr_.9fr_.8fr] md:items-center">
                    <div>
                      <p className="text-[10px] font-bold text-slate-400">{L("العميل", "Client")}</p>
                      <p className="font-black text-slate-900">{client.leadName || client.competentPerson || `#${client.id}`}</p>
                      <p className="text-[11px] text-slate-500" dir="ltr">{client.phone || client.contactPhone || "—"}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400">{L("الدورة", "Course")}</p>
                      <p className="font-bold text-slate-800">{client.primaryCourseName || "—"}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400">{L("المصدر", "Source")}</p>
                      <Badge variant="outline">{client.primaryMarketerCode || client.primaryCrmTag || "—"}</Badge>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold text-slate-400">{L("الدفع", "Payment")}</p>
                      <div className="flex items-center gap-2">
                        <WalletCards className="h-3.5 w-3.5 text-emerald-600" />
                        <span className="font-black text-slate-800">{client.primaryPaymentStatus || "—"}</span>
                      </div>
                      <p className="text-[11px] text-slate-500">{client.primaryPaidAmount ?? "0"} SAR</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </CRMLayout>
  );
}
'''

changed = []

try:
    if ensure_crm_layout(MARKETERS):
        changed.append("client/src/pages/affiliate/MarketersPage.tsx")
    if ensure_crm_layout(COURSES):
        changed.append("client/src/pages/affiliate/CoursesPage.tsx")
except RuntimeError as exc:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print(f"ERROR={exc}")
    sys.exit(2)

current_sub = SUBSCRIPTIONS.read_text(encoding="utf-8")
if current_sub != SUBSCRIPTIONS_CONTENT:
    backup(SUBSCRIPTIONS)
    SUBSCRIPTIONS.write_text(SUBSCRIPTIONS_CONTENT, encoding="utf-8")
    changed.append("client/src/pages/affiliate/SubscriptionsPage.tsx")

# Final guards
for p in (MARKETERS, COURSES, SUBSCRIPTIONS):
    text = p.read_text(encoding="utf-8")
    if 'from "@/components/CRMLayout"' not in text or "<CRMLayout" not in text:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=CRM_LAYOUT_GUARD_FAILED:{p.name}")
        sys.exit(3)

sub = SUBSCRIPTIONS.read_text(encoding="utf-8")
for marker in [
    "createClientWithCourseSubscription",
    "listCourseProducts",
    "listMarketers",
    "listClients",
    "paymentStatus",
    "secondaryMarketerCode",
]:
    if marker not in sub:
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=SUBSCRIPTIONS_WIRING_MISSING:{marker}")
        sys.exit(4)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + ";".join(changed))
print("MARKETERS_LAYOUT=YES")
print("COURSES_LAYOUT=YES")
print("SUBSCRIPTIONS_LAYOUT=YES")
print("SUBSCRIPTIONS_RECOVERY=FULL_STANDALONE")
print("BACKEND_DB_AUTH=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
