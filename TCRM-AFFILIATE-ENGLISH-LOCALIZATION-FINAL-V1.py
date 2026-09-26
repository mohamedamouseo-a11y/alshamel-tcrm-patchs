#!/usr/bin/env python3
from pathlib import Path
import sys

PATCH = "TCRM-AFFILIATE-ENGLISH-LOCALIZATION-FINAL-V1"
ROOT = Path("/var/www/TCRM-MAIN")
if not ROOT.exists():
    ROOT = Path("/var/www/tamiyouz_crm")

FILES = {
    "marketers": ROOT / "client/src/pages/affiliate/MarketersPage.tsx",
    "courses": ROOT / "client/src/pages/affiliate/CoursesPage.tsx",
    "commissions": ROOT / "client/src/pages/affiliate/CommissionsPage.tsx",
}

for p in FILES.values():
    if not p.exists():
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=MISSING_FILE:{p}")
        sys.exit(1)

def rep(src, old, new, label):
    if old not in src:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=ANCHOR_MISSING:{label}")
        sys.exit(2)
    return src.replace(old, new)

# ---------- Marketers ----------
p = FILES["marketers"]
s = p.read_text(encoding="utf-8")
if 'import { useLanguage } from "@/contexts/LanguageContext";' not in s:
    s = rep(s,
        'import { trpc } from "@/lib/trpc";\n',
        'import { trpc } from "@/lib/trpc";\nimport { useLanguage } from "@/contexts/LanguageContext";\n',
        "marketers_language_import"
    )
s = s.replace('function L(ar: string, en: string) { return ar; }\n\n', '')
s = rep(s,
    'export default function MarketersPage() {\n',
    'export default function MarketersPage() {\n  const { isRTL } = useLanguage();\n  const L = (ar: string, en: string) => (isRTL ? ar : en);\n',
    "marketers_local_L"
)
marketer_repls = {
    'toast.success("تم إضافة المسوق بنجاح");': 'toast.success(L("تم إضافة المسوق بنجاح", "Marketer added successfully"));',
    'toast.error("الاسم والكود مطلوبان");': 'toast.error(L("الاسم والكود مطلوبان", "Name and code are required"));',
    '<p className="text-xs text-slate-500">إضافة مسوق جديد وربطه بكود ثابت</p>': '<p className="text-xs text-slate-500">{L("إضافة مسوق جديد وربطه بكود ثابت", "Add a new marketer and assign a fixed code")}</p>',
    'placeholder="اسم المسوق"': 'placeholder={L("اسم المسوق", "Marketer name")}',
    'placeholder="الجوال"': 'placeholder={L("الجوال", "Phone")}',
    'placeholder="ملاحظات المسوق / بيانات إضافية للصرف أو التواصل"': 'placeholder={L("ملاحظات المسوق / بيانات إضافية للصرف أو التواصل", "Marketer notes / additional payout or contact details")}',
    '<p className="text-sm font-black text-slate-900">المسوقون الحاليون</p>': '<p className="text-sm font-black text-slate-900">{L("المسوقون الحاليون", "Current Marketers")}</p>',
    '<p className="text-xs text-slate-500">الأكواد النشطة ومعلومات التواصل</p>': '<p className="text-xs text-slate-500">{L("الأكواد النشطة ومعلومات التواصل", "Active codes and contact information")}</p>',
    '                لا يوجد مسوقون بعد.': '                {L("لا يوجد مسوقون بعد.", "No marketers yet.")}',
}
for old,new in marketer_repls.items():
    if old in s: s = s.replace(old,new)
p.write_text(s, encoding="utf-8")

# ---------- Courses ----------
p = FILES["courses"]
s = p.read_text(encoding="utf-8")
if 'import { useLanguage } from "@/contexts/LanguageContext";' not in s:
    s = rep(s,
        'import { trpc } from "@/lib/trpc";\n',
        'import { trpc } from "@/lib/trpc";\nimport { useLanguage } from "@/contexts/LanguageContext";\n',
        "courses_language_import"
    )
s = s.replace('function L(ar: string, en: string) { return ar; }\n', '')
s = rep(s,
    'export default function CoursesPage() {\n',
    'export default function CoursesPage() {\nconst { isRTL } = useLanguage();\nconst L = (ar: string, en: string) => (isRTL ? ar : en);\n',
    "courses_local_L"
)
course_repls = {
    'toast.success("تم إضافة الدورة بنجاح");': 'toast.success(L("تم إضافة الدورة بنجاح", "Course added successfully"));',
    'toast.success("تم تحديث الدورة بنجاح");': 'toast.success(L("تم تحديث الدورة بنجاح", "Course updated successfully"));',
    'toast.error("اسم الدورة مطلوب")': 'toast.error(L("اسم الدورة مطلوب", "Course name is required"))',
    '<p className="text-xs text-slate-500">إضافة دورة وسعر وعمولة الفرد</p>': '<p className="text-xs text-slate-500">{L("إضافة دورة وسعر وعمولة الفرد", "Add a course, price, and per-subscriber commission")}</p>',
    'placeholder="اسم الدورة"': 'placeholder={L("اسم الدورة", "Course name")}',
    '<SelectItem value="InstituteEmaar">معهد إعمار</SelectItem>': '<SelectItem value="InstituteEmaar">{L("معهد إعمار", "Emaar Institute")}</SelectItem>',
    '<SelectItem value="GoldenEmaar">مؤسسة إعمار الذهبية</SelectItem>': '<SelectItem value="GoldenEmaar">{L("مؤسسة إعمار الذهبية", "Golden Emaar Foundation")}</SelectItem>',
    '<SelectItem value="Other">أخرى</SelectItem>': '<SelectItem value="Other">{L("أخرى", "Other")}</SelectItem>',
    'placeholder="السعر الكامل"': 'placeholder={L("السعر الكامل", "Full price")}',
    'placeholder="عمولة الفرد"': 'placeholder={L("عمولة الفرد", "Per-subscriber commission")}',
    '<label className="text-[11px] text-muted-foreground">تاريخ إغلاق التسجيل</label>': '<label className="text-[11px] text-muted-foreground">{L("تاريخ إغلاق التسجيل", "Registration close date")}</label>',
    'aria-label="تاريخ إغلاق التسجيل"': 'aria-label={L("تاريخ إغلاق التسجيل", "Registration close date")}',
    '<label className="text-[11px] text-muted-foreground">تاريخ بداية الدورة</label>': '<label className="text-[11px] text-muted-foreground">{L("تاريخ بداية الدورة", "Course start date")}</label>',
    'aria-label="تاريخ بداية الدورة"': 'aria-label={L("تاريخ بداية الدورة", "Course start date")}',
    '<SelectItem value="NotStarted">لم تبدأ</SelectItem>': '<SelectItem value="NotStarted">{L("لم تبدأ", "Not started")}</SelectItem>',
    '<SelectItem value="RegistrationOpen">التسجيل مفتوح</SelectItem>': '<SelectItem value="RegistrationOpen">{L("التسجيل مفتوح", "Registration open")}</SelectItem>',
    '<SelectItem value="RegistrationClosed">التسجيل مغلق</SelectItem>': '<SelectItem value="RegistrationClosed">{L("التسجيل مغلق", "Registration closed")}</SelectItem>',
    '<SelectItem value="Started">بدأت</SelectItem>': '<SelectItem value="Started">{L("بدأت", "Started")}</SelectItem>',
    '<SelectItem value="Ended">انتهت</SelectItem>': '<SelectItem value="Ended">{L("انتهت", "Ended")}</SelectItem>',
    'placeholder="ملاحظات"': 'placeholder={L("ملاحظات", "Notes")}',
    '<p className="text-sm font-black text-slate-900">الدورات الحالية</p>': '<p className="text-sm font-black text-slate-900">{L("الدورات الحالية", "Current Courses")}</p>',
    '<p className="text-xs text-slate-500">بيانات الدورة والعمولة وحالة التسجيل</p>': '<p className="text-xs text-slate-500">{L("بيانات الدورة والعمولة وحالة التسجيل", "Course, commission, and registration details")}</p>',
    '<SelectItem value="RegistrationOpen">مفتوح</SelectItem>': '<SelectItem value="RegistrationOpen">{L("مفتوح", "Open")}</SelectItem>',
    '<SelectItem value="RegistrationClosed">مغلق</SelectItem>': '<SelectItem value="RegistrationClosed">{L("مغلق", "Closed")}</SelectItem>',
    '<SelectItem value="active">مفعلة</SelectItem>': '<SelectItem value="active">{L("مفعلة", "Active")}</SelectItem>',
    '<SelectItem value="inactive">معطلة</SelectItem>': '<SelectItem value="inactive">{L("معطلة", "Inactive")}</SelectItem>',
    '<Button size="sm" variant="outline" onClick={cancelEditCourse}>إلغاء</Button>': '<Button size="sm" variant="outline" onClick={cancelEditCourse}>{L("إلغاء", "Cancel")}</Button>',
    '<Button size="sm" disabled={updateCourseM.isPending} onClick={submitUpdateCourse}>حفظ الدورة</Button>': '<Button size="sm" disabled={updateCourseM.isPending} onClick={submitUpdateCourse}>{L("حفظ الدورة", "Save Course")}</Button>',
    '{course.isActive === 0 ? "معطلة" : "مفعلة"}': '{course.isActive === 0 ? L("معطلة", "Inactive") : L("مفعلة", "Active")}',
    '<span className="font-semibold text-slate-600">السعر:</span>': '<span className="font-semibold text-slate-600">{L("السعر:", "Price:")}</span>',
    '<span className="font-semibold text-slate-600">العمولة:</span>': '<span className="font-semibold text-slate-600">{L("العمولة:", "Commission:")}</span>',
    '<span className="font-semibold text-slate-600">إغلاق:</span>': '<span className="font-semibold text-slate-600">{L("إغلاق:", "Closes:")}</span>',
    '<span className="font-semibold text-slate-600">بداية:</span>': '<span className="font-semibold text-slate-600">{L("بداية:", "Starts:")}</span>',
    '{course.isActive === 0 ? "تفعيل" : "تعطيل"}': '{course.isActive === 0 ? L("تفعيل", "Activate") : L("تعطيل", "Deactivate")}',
    '>تعديل</Button>': '>{L("تعديل", "Edit")}</Button>',
    '>لا توجد دورات بعد.</div>': '>{L("لا توجد دورات بعد.", "No courses yet.")}</div>',
}
for old,new in course_repls.items():
    if old in s: s = s.replace(old,new)
p.write_text(s, encoding="utf-8")

# ---------- Commissions ----------
p = FILES["commissions"]
s = p.read_text(encoding="utf-8")
if 'import { useLanguage } from "@/contexts/LanguageContext";' not in s:
    s = rep(s,
        'import { useAuth } from "@/_core/hooks/useAuth";\n',
        'import { useAuth } from "@/_core/hooks/useAuth";\nimport { useLanguage } from "@/contexts/LanguageContext";\n',
        "commissions_language_import"
    )
s = rep(s,
    'export default function CommissionsPage() {\n  const { user } = useAuth();\n',
    'export default function CommissionsPage() {\n  const { user } = useAuth();\n  const { isRTL } = useLanguage();\n  const L = (ar: string, en: string) => (isRTL ? ar : en);\n',
    "commissions_local_L"
)

# Mutation toasts / permission
s = s.replace('toast.success("تم تحديث الفاتورة")', 'toast.success(L("تم تحديث الفاتورة", "Invoice updated"))')
s = s.replace('toast.success("تم إنشاء الفاتورة: " + r.invoiceNumber)', 'toast.success(L("تم إنشاء الفاتورة: ", "Invoice created: ") + r.invoiceNumber)')
s = s.replace('toast.success("تم تحديث الفاتورة: " + r.invoiceNumber)', 'toast.success(L("تم تحديث الفاتورة: ", "Invoice refreshed: ") + r.invoiceNumber)')
s = s.replace('toast.success("تم إلغاء الفاتورة")', 'toast.success(L("تم إلغاء الفاتورة", "Invoice cancelled"))')
s = s.replace('toast.success("تم إغلاق الشهر بنجاح")', 'toast.success(L("تم إغلاق الشهر بنجاح", "Month closed successfully"))')
s = s.replace('toast.error("صلاحية المدير أو مدير المبيعات مطلوبة")', 'toast.error(L("صلاحية المدير أو مدير المبيعات مطلوبة", "Admin or Sales Manager permission is required"))')

# KPI cards
s = s.replace('{ step: "1", label: "مشتركين جدد", value: visibleDashboardKpis?.newSubscribers ?? 0, hint: "حسب الشهر المختار",', '{ step: "1", label: L("مشتركين جدد", "New subscribers"), value: visibleDashboardKpis?.newSubscribers ?? 0, hint: L("حسب الشهر المختار", "For selected month"),')
s = s.replace('{ step: "2", label: "أفضل مسوق", value: visibleDashboardKpis?.topMarketer?.marketerCode ?? "—", hint: visibleDashboardKpis?.topMarketer?.marketerName ?? "حسب عدد المشتركين",', '{ step: "2", label: L("أفضل مسوق", "Top marketer"), value: visibleDashboardKpis?.topMarketer?.marketerCode ?? "—", hint: visibleDashboardKpis?.topMarketer?.marketerName ?? L("حسب عدد المشتركين", "By subscriber count"),')
s = s.replace('{ step: "3", label: "أكثر دورة طلبًا", value: visibleDashboardKpis?.topCourse?.courseName ?? "—", hint: "أعلى عدد مشتركين",', '{ step: "3", label: L("أكثر دورة طلبًا", "Top course"), value: visibleDashboardKpis?.topCourse?.courseName ?? "—", hint: L("أعلى عدد مشتركين", "Highest subscriber count"),')
s = s.replace('{ step: "4", label: "إجمالي العمولات", value: reportCommissionTotal.toFixed(2), hint: reportSubscriberTotal + " مشترك محتسب",', '{ step: "4", label: L("إجمالي العمولات", "Total commissions"), value: reportCommissionTotal.toFixed(2), hint: reportSubscriberTotal + " " + L("مشترك محتسب", "counted subscribers"),')
s = s.replace('{ step: "5", label: "فواتير مفتوحة", value: invoiceOpenCount, hint: invoicePendingCount + " معلقة / " + invoicePartialCount + " جزئية",', '{ step: "5", label: L("فواتير مفتوحة", "Open invoices"), value: invoiceOpenCount, hint: invoicePendingCount + " " + L("معلقة", "pending") + " / " + invoicePartialCount + " " + L("جزئية", "partial"),')

# Visible JSX literals
pairs = [
("العمولات والتقارير","Commissions & Reports"),
("إدارة عمولات المسوقين والفواتير الشهرية","Manage marketer commissions and monthly invoices"),
("شهر مغلق","Closed month"),
("تصدير Excel","Export Excel"),
("إغلاق الشهر","Close month"),
("تأكيد إغلاق شهر ","Confirm closing month "),
("سيتم إنشاء Snapshot مختوم للتقرير والفواتير. بعد الإغلاق لن يمكن تعديل أي اشتراك أو فاتورة تؤثر على هذا الشهر.","A sealed snapshot of the report and invoices will be created. After closing, subscriptions or invoices affecting this month cannot be modified."),
("إلغاء","Cancel"),
("تأكيد الإغلاق","Confirm close"),
("فواتير مدفوعة","Paid invoices"),
("عمولات مدفوعة","Paid commissions"),
("عمولات معلقة","Pending commissions"),
("جدول العمولات المستحقة","Due commissions"),
("راجع المسوق، الدورة، عدد المشتركين، والإجمالي قبل إصدار الفاتورة.","Review marketer, course, subscriber count, and total before issuing an invoice."),
("المسوق","Marketer"),
("الدورة","Course"),
("العدد","Count"),
("الإجمالي","Total"),
("إنشاء فاتورة","Create invoice"),
("فاتورة موجودة","Invoice exists"),
("تحديث","Refresh"),
("لا توجد عمولات مستحقة لهذا الشهر.","No commissions are due for this month."),
("فواتير العمولات وتفاصيل الصرف","Commission invoices & payout details"),
("سجّل الصرف والخصم وجدول الدفعات لكل فاتورة.","Track payouts, deductions, and payout schedules for each invoice."),
("فاتورة","invoice"),
("رقم الفاتورة","Invoice number"),
("المدفوع","Paid"),
("الحالة","Status"),
("تعليم كمدفوعة","Mark paid"),
("حالة الفاتورة","Invoice status"),
("طريقة الصرف","Payout method"),
("معلقة","Pending"),
("جزئية","Partial"),
("مدفوعة","Paid"),
("تحويل بنكي","Bank transfer"),
("كاش","Cash"),
("أخرى","Other"),
("المبلغ المدفوع","Paid amount"),
("رقم الحوالة","Transfer reference"),
("مبلغ الخصم","Deduction amount"),
("سبب الخصم","Deduction reason"),
("موعد الصرف المتوقع","Expected payment date"),
("رابط إثبات الصرف","Proof URL"),
("سبب التأخير","Delay reason"),
("ملاحظات الصرف","Payout notes"),
("جدول الدفعات المقسطة","Payout schedule"),
("إجمالي الدفعات لا يجب أن يتجاوز إجمالي الفاتورة.","Scheduled payouts must not exceed the invoice total."),
("إضافة دفعة","Add payout"),
("حذف","Remove"),
("مبلغ الدفعة","Payout amount"),
("تاريخ الاستحقاق","Due date"),
("تاريخ الدفع","Paid at"),
("ملاحظات","Notes"),
("لا توجد دفعات مجدولة.","No scheduled payouts."),
("حفظ تفاصيل الصرف","Save payout details"),
("لا توجد فواتير لهذا الشهر.","No invoices for this month."),
]
# exact text-node replacements where safe
for ar,en in pairs:
    s = s.replace(f'>{ar}</', f'>{{L("{ar}", "{en}")}}</')
# count badge
s = s.replace('{visibleCommissionReport.length} صف', '{visibleCommissionReport.length} {L("صف", "rows")}')
s = s.replace('{visibleCommissionInvoices.length} فاتورة', '{visibleCommissionInvoices.length} {L("فاتورة", "invoices")}')
# closed snapshot line
s = s.replace(
    '>هذا عرض التقرير المختوم لشهر {commissionMonth}. تاريخ الإغلاق: {(closedMonthRecord as any)?.closedAt ?? "—"}.</div>',
    '>{L("هذا عرض التقرير المختوم لشهر", "Showing the sealed report for month")} {commissionMonth}. {L("تاريخ الإغلاق:", "Closed at:")} {(closedMonthRecord as any)?.closedAt ?? "—"}.</div>'
)
# alert title with interpolation
s = s.replace(
    '<AlertDialogTitle>تأكيد إغلاق شهر {commissionMonth}</AlertDialogTitle>',
    '<AlertDialogTitle>{L("تأكيد إغلاق شهر", "Confirm closing month")} {commissionMonth}</AlertDialogTitle>'
)
# cancel prompt visible to user
s = s.replace(
    'window.prompt("اكتب سبب إلغاء الفاتورة:", "إلغاء فاتورة اختبارية")',
    'window.prompt(L("اكتب سبب إلغاء الفاتورة:", "Enter invoice cancellation reason:"), L("إلغاء فاتورة اختبارية", "Test invoice cancellation"))'
)
# payout row dynamic label
s = s.replace('>دفعة رقم {index + 1}</p>', '>{L("دفعة رقم", "Payout #")} {index + 1}</p>')

p.write_text(s, encoding="utf-8")

# ---------- Verification ----------
checks = []
for key,p in FILES.items():
    c = p.read_text(encoding="utf-8")
    checks.append((key, c))

failures = []
for key,c in checks:
    if key in ("marketers","courses") and 'function L(ar: string, en: string) { return ar; }' in c:
        failures.append(f"{key}:forced_arabic_L")
    if 'useLanguage' not in c or 'isRTL ? ar : en' not in c:
        failures.append(f"{key}:language_binding_missing")

# Known visible Arabic that must no longer be bare.
must_be_gone = {
    "marketers": ['placeholder="اسم المسوق"', '>المسوقون الحاليون</p>', 'لا يوجد مسوقون بعد.\n'],
    "courses": ['>الدورات الحالية</p>', '>لا توجد دورات بعد.</div>', '>تعديل</Button>', '>إلغاء</Button>'],
    "commissions": ['>العمولات والتقارير</h1>', '>إغلاق الشهر</Button>', '>إنشاء فاتورة</Button>', '>حفظ تفاصيل الصرف</Button>'],
}
for key,needles in must_be_gone.items():
    c = FILES[key].read_text(encoding="utf-8")
    for n in needles:
        if n in c:
            failures.append(f"{key}:bare_arabic:{n}")

if failures:
    print(f"PATCH={PATCH}")
    print("APPLY=FAIL")
    print("ERROR=" + "|".join(failures))
    sys.exit(3)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=client/src/pages/affiliate/MarketersPage.tsx;client/src/pages/affiliate/CoursesPage.tsx;client/src/pages/affiliate/CommissionsPage.tsx")
print("ENGLISH_UI=LOCALIZED")
print("ARABIC_UI=PRESERVED")
print("API_ENUMS=UNCHANGED")
print("BUSINESS_LOGIC=UNCHANGED")
print("DB=UNCHANGED")
print("COMMIT=NO")
print("PUSH=NO")
