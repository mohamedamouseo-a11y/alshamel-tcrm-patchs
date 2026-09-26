#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
import os, shutil, sys

PATCH = "TCRM-AFFILIATE-INVOICES-STANDALONE-P5-V1"
ROOT = Path(os.environ.get("TCRM_ROOT", "/var/www/tamiyouz_crm"))
PAGE = ROOT / "client/src/pages/affiliate/InvoicesPage.tsx"
APP = ROOT / "client/src/App.tsx"
LAYOUT = ROOT / "client/src/components/CRMLayout.tsx"

for p in (APP, LAYOUT):
    if not p.exists():
        print(f"PATCH={PATCH}")
        print("APPLY=FAIL")
        print(f"ERROR=MISSING:{p}")
        sys.exit(1)

PAGE_CONTENT = r'''import { useState } from "react";
import CRMLayout from "@/components/CRMLayout";
import { trpc } from "@/lib/trpc";
import { useAuth } from "@/_core/hooks/useAuth";
import { useLanguage } from "@/contexts/LanguageContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Archive, Calendar, RefreshCw, WalletCards } from "lucide-react";
import { toast } from "sonner";

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

export default function InvoicesPage() {
  const { user } = useAuth();
  const { isRTL } = useLanguage();
  const L = (ar: string, en: string) => (isRTL ? ar : en);
  const canManage = canManageRole(user?.role);
  const [month, setMonth] = useState(currentRiyadhMonth);
  const [forms, setForms] = useState<Record<number, any>>({});

  const invoicesQ = trpc.accountManagement.listEmaarCommissionInvoices.useQuery({ month });
  const closedMonthsQ = trpc.accountManagement.listEmaarClosedMonths.useQuery();
  const closedMonths = closedMonthsQ.data ?? [];
  const closedMonth = closedMonths.find((item: any) => item.periodMonth === month);
  const isClosed = Boolean(closedMonth);
  const closedSummary = getClosedSummary((closedMonth as any)?.summaryJson);
  const liveInvoices = invoicesQ.data ?? [];
  const invoices = isClosed ? (closedSummary?.invoices ?? liveInvoices) : liveInvoices;

  const updateM = trpc.accountManagement.updateEmaarCommissionInvoiceStatus.useMutation({
    onSuccess: async () => {
      await invoicesQ.refetch();
      toast.success(L("تم تحديث الفاتورة", "Invoice updated"));
    },
    onError: (error) => toast.error(error.message),
  });

  const refreshM = trpc.accountManagement.refreshEmaarCommissionInvoiceFromReport.useMutation({
    onSuccess: async (result) => {
      await invoicesQ.refetch();
      toast.success(L(`تم تحديث الفاتورة: ${result.invoiceNumber}`, `Invoice refreshed: ${result.invoiceNumber}`));
    },
    onError: (error) => toast.error(error.message),
  });

  const cancelM = trpc.accountManagement.cancelEmaarCommissionInvoice.useMutation({
    onSuccess: async (result) => {
      await invoicesQ.refetch();
      toast.success(L(`تم إلغاء الفاتورة: ${result.invoiceNumber}`, `Invoice cancelled: ${result.invoiceNumber}`));
    },
    onError: (error) => toast.error(error.message),
  });

  function getForm(inv: any) {
    return forms[inv.id] ?? {
      status: inv.status ?? "Pending",
      payoutMethod: inv.payoutMethod ?? "BankTransfer",
      paidAmount: String(inv.paidAmount ?? ""),
      deductionAmount: String(inv.deductionAmount ?? ""),
      deductionReason: inv.deductionReason ?? "",
      delayReason: inv.delayReason ?? "",
      expectedPaymentDate: inv.expectedPaymentDate ?? "",
      transferReference: inv.transferReference ?? "",
      proofUrl: inv.proofUrl ?? "",
      payoutSchedule: Array.isArray(inv.payoutSchedule)
        ? inv.payoutSchedule.map((row: any) => ({
            amount: String(row?.amount ?? ""),
            dueDate: row?.dueDate ?? "",
            paidAt: row?.paidAt ?? "",
            reference: row?.reference ?? "",
            notes: row?.notes ?? "",
          }))
        : [],
      notes: inv.notes ?? "",
    };
  }

  function setField(invoiceId: number, inv: any, key: string, value: string) {
    const current = getForm(inv);
    setForms((prev) => ({ ...prev, [invoiceId]: { ...current, [key]: value } }));
  }

  function setScheduleField(invoiceId: number, inv: any, index: number, key: string, value: string) {
    const current = getForm(inv);
    const payoutSchedule = [...(current.payoutSchedule ?? [])];
    payoutSchedule[index] = {
      amount: "",
      dueDate: "",
      paidAt: "",
      reference: "",
      notes: "",
      ...(payoutSchedule[index] ?? {}),
      [key]: value,
    };
    setForms((prev) => ({ ...prev, [invoiceId]: { ...current, payoutSchedule } }));
  }

  function addScheduleRow(invoiceId: number, inv: any) {
    const current = getForm(inv);
    const payoutSchedule = [...(current.payoutSchedule ?? []), { amount: "", dueDate: "", paidAt: "", reference: "", notes: "" }];
    setForms((prev) => ({ ...prev, [invoiceId]: { ...current, payoutSchedule } }));
  }

  function removeScheduleRow(invoiceId: number, inv: any, index: number) {
    const current = getForm(inv);
    const payoutSchedule = (current.payoutSchedule ?? []).filter((_: any, i: number) => i !== index);
    setForms((prev) => ({ ...prev, [invoiceId]: { ...current, payoutSchedule } }));
  }

  function validate(inv: any, form: any): boolean {
    const proofUrl = String(form.proofUrl ?? "").trim();
    if (proofUrl.startsWith("data:")) {
      toast.error(L("إثبات التحويل يجب أن يكون رابط خارجي فقط", "Proof must be an external URL"));
      return false;
    }
    if (proofUrl && !/^https?:\/\//i.test(proofUrl)) {
      toast.error(L("رابط الإثبات يجب أن يبدأ بـ http:// أو https://", "Proof URL must start with http:// or https://"));
      return false;
    }

    const total = parseMoney(inv.totalCommission);
    const paid = parseMoney(form.paidAmount);
    const deduction = parseMoney(form.deductionAmount);
    if (paid + deduction - total > 0.01) {
      toast.error(L("المدفوع + الخصم لا يجب أن يتجاوز إجمالي الفاتورة", "Paid + deduction cannot exceed invoice total"));
      return false;
    }
    if (form.status === "Paid" && total > 0 && paid <= 0) {
      toast.error(L("الفاتورة المدفوعة تحتاج مبلغًا مدفوعًا أكبر من صفر", "Paid invoice requires a positive paid amount"));
      return false;
    }
    if (form.status === "Paid" && Math.abs((paid + deduction) - total) > 0.01) {
      toast.error(L("لإغلاق الفاتورة كمدفوعة يجب أن يساوي المدفوع + الخصم الإجمالي", "Paid + deduction must equal total"));
      return false;
    }
    if (form.status === "Partial" && (paid + deduction <= 0 || paid + deduction >= total)) {
      toast.error(L("الفاتورة الجزئية تحتاج مبلغًا أكبر من صفر وأقل من الإجمالي", "Partial invoice requires an amount between zero and total"));
      return false;
    }

    const rows = (form.payoutSchedule ?? []).filter((row: any) =>
      [row.amount, row.dueDate, row.paidAt, row.reference, row.notes].some((v) => String(v ?? "").trim()),
    );
    for (const row of rows) {
      if (parseMoney(row.amount) <= 0 || !String(row.dueDate ?? "").trim()) {
        toast.error(L("كل دفعة مجدولة تحتاج مبلغًا صحيحًا وتاريخ استحقاق", "Each scheduled payout needs amount and due date"));
        return false;
      }
    }
    if (rows.reduce((sum: number, row: any) => sum + parseMoney(row.amount), 0) - total > 0.01) {
      toast.error(L("إجمالي الدفعات المجدولة لا يجب أن يتجاوز إجمالي الفاتورة", "Scheduled payouts cannot exceed invoice total"));
      return false;
    }
    return true;
  }

  async function save(inv: any, forcePaid = false) {
    const form = getForm(inv);
    const forcePaidAmount = Math.max(0, parseMoney(inv.totalCommission) - parseMoney(form.deductionAmount)).toFixed(2);
    const next = forcePaid ? { ...form, status: "Paid", paidAmount: forcePaidAmount } : form;
    if (!validate(inv, next)) return;

    await updateM.mutateAsync({
      id: Number(inv.id),
      status: next.status,
      payoutMethod: next.payoutMethod,
      paidAmount: next.paidAmount || "0",
      deductionAmount: next.deductionAmount || "0",
      deductionReason: next.deductionReason || undefined,
      delayReason: next.delayReason || undefined,
      expectedPaymentDate: next.expectedPaymentDate || undefined,
      transferReference: next.transferReference || undefined,
      proofUrl: String(next.proofUrl ?? "").trim() || null,
      payoutSchedule: (next.payoutSchedule ?? []).filter((row: any) =>
        [row.amount, row.dueDate, row.paidAt, row.reference, row.notes].some((v) => String(v ?? "").trim()),
      ),
      notes: next.notes || undefined,
    });
  }

  function refresh(inv: any) {
    if (!canManage || isClosed) return;
    if (!window.confirm(L("تحديث الفاتورة حسب تقرير العمولات الحالي؟", "Refresh invoice from the current commission report?"))) return;
    refreshM.mutate({ id: Number(inv.id) });
  }

  function cancel(inv: any) {
    if (!canManage || isClosed) return;
    const reason = window.prompt(L("اكتب سبب إلغاء الفاتورة:", "Enter cancellation reason:"), "");
    if (reason === null) return;
    const clean = reason.trim();
    if (clean.length < 3) {
      toast.error(L("سبب الإلغاء مطلوب", "Cancellation reason is required"));
      return;
    }
    cancelM.mutate({ id: Number(inv.id), reason: clean });
  }

  const paidCount = invoices.filter((inv: any) => inv.status === "Paid").length;
  const partialCount = invoices.filter((inv: any) => inv.status === "Partial").length;
  const pendingCount = invoices.filter((inv: any) => inv.status === "Pending").length;

  return (
    <CRMLayout>
      <div className="p-4 md:p-6 space-y-5" dir={isRTL ? "rtl" : "ltr"}>
        <div className="flex flex-col gap-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-[#1e3a5f] to-[#6366f1] text-white shadow-lg">
              <Archive className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-black text-slate-950">{L("الفواتير والصرف", "Invoices & Payouts")}</h1>
              <p className="text-sm text-slate-500">{L("إدارة فواتير العمولات، المدفوعات، الخصومات والدفعات المجدولة.", "Manage commission invoices, payouts, deductions and schedules.")}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {isClosed && <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-800">{L("شهر مغلق", "Closed month")}</Badge>}
            <Calendar className="h-4 w-4 text-slate-400" />
            <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-44" />
            <Button variant="outline" size="sm" onClick={() => invoicesQ.refetch()} disabled={invoicesQ.isFetching}>
              <RefreshCw className={`h-4 w-4 ${invoicesQ.isFetching ? "animate-spin" : ""}`} />
              {L("تحديث", "Refresh")}
            </Button>
          </div>
        </div>

        {!canManage && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            {L("وضع عرض فقط: تعديل تفاصيل الصرف متاح للمدير أو مدير المبيعات فقط.", "Read-only mode: payout editing is limited to Admin or Sales Manager.")}
          </div>
        )}

        {isClosed && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            {L("هذا الشهر مغلق؛ البيانات المعروضة من Snapshot الإغلاق وغير قابلة للتعديل.", "This month is closed; shown data comes from the closing snapshot and is read-only.")}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div className="rounded-2xl border bg-white p-4 shadow-sm"><p className="text-xs text-slate-500">{L("إجمالي الفواتير", "Total invoices")}</p><p className="mt-1 text-2xl font-black">{invoices.length}</p></div>
          <div className="rounded-2xl border bg-emerald-50 p-4"><p className="text-xs text-emerald-700">{L("مدفوعة", "Paid")}</p><p className="mt-1 text-2xl font-black text-emerald-800">{paidCount}</p></div>
          <div className="rounded-2xl border bg-amber-50 p-4"><p className="text-xs text-amber-700">{L("جزئية", "Partial")}</p><p className="mt-1 text-2xl font-black text-amber-800">{partialCount}</p></div>
          <div className="rounded-2xl border bg-slate-50 p-4"><p className="text-xs text-slate-600">{L("معلقة", "Pending")}</p><p className="mt-1 text-2xl font-black text-slate-800">{pendingCount}</p></div>
        </div>

        <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-col gap-2 bg-gradient-to-l from-slate-950 via-[#1e3a5f] to-[#6366f1] px-4 py-3 text-white sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-black">{L("فواتير العمولات وتفاصيل الصرف", "Commission invoices & payout details")}</p>
              <p className="text-[11px] text-blue-50/80">{L("سجل المدفوع، الخصم، مرجع التحويل والدفعات المجدولة لكل فاتورة.", "Track paid amount, deductions, transfer references and payout schedules.")}</p>
            </div>
            <Badge className="w-fit rounded-full border-white/20 bg-white/15 text-white hover:bg-white/20">{invoices.length} {L("فاتورة", "invoices")}</Badge>
          </div>

          <div className="space-y-4 p-3">
            {invoicesQ.isLoading && !isClosed && <p className="p-4 text-sm text-slate-500">{L("جاري التحميل...", "Loading...")}</p>}

            {invoices.map((inv: any) => {
              const form = getForm(inv);
              return (
                <div key={inv.id} className="space-y-4 rounded-3xl border border-slate-200 bg-slate-50/60 p-4 text-xs shadow-sm">
                  <div className="grid grid-cols-1 gap-3 rounded-2xl border border-slate-100 bg-white p-3 md:grid-cols-[1.4fr_.9fr_.9fr_.9fr_.7fr_1.3fr] md:items-center">
                    <div><p className="text-[10px] font-bold text-slate-400">{L("رقم الفاتورة", "Invoice")}</p><p className="truncate font-black text-slate-900">{inv.invoiceNumber}</p></div>
                    <div><p className="text-[10px] font-bold text-slate-400">{L("المسوق", "Marketer")}</p><Badge variant="outline" className="rounded-full bg-blue-50 text-[#1e3a5f]">{inv.marketerCode}</Badge></div>
                    <div><p className="text-[10px] font-bold text-slate-400">{L("الإجمالي", "Total")}</p><p className="font-black text-emerald-700">{inv.totalCommission}</p></div>
                    <div><p className="text-[10px] font-bold text-slate-400">{L("المدفوع", "Paid")}</p><p className="font-black text-slate-900">{inv.paidAmount ?? "0.00"}</p></div>
                    <div><p className="text-[10px] font-bold text-slate-400">{L("الحالة", "Status")}</p><Badge variant="outline" className="w-fit rounded-full bg-white">{inv.status}</Badge></div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button size="sm" disabled={!canManage || isClosed || updateM.isPending || inv.status === "Paid"} onClick={() => save(inv, true)} className="h-9 rounded-2xl bg-gradient-to-r from-[#1e3a5f] to-[#6366f1] px-3 text-xs font-black text-white">{L("تعليم كمدفوعة", "Mark paid")}</Button>
                      <Button size="sm" variant="outline" disabled={!canManage || isClosed || refreshM.isPending} onClick={() => refresh(inv)}>{L("تحديث", "Refresh")}</Button>
                      <Button size="sm" variant="outline" disabled={!canManage || isClosed || cancelM.isPending} onClick={() => cancel(inv)} className="text-red-700">{L("إلغاء", "Cancel")}</Button>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-indigo-100 bg-indigo-50/40 p-3">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <div><p className="text-[11px] font-bold text-indigo-950">{L("تفاصيل الدورات المرتبطة", "Linked course details")}</p></div>
                      <Badge variant="outline" className="rounded-full border-indigo-200 bg-white/80 text-indigo-700">{(inv.items?.length ?? 0) || (inv.courseName ? 1 : 0)}</Badge>
                    </div>
                    <div className="overflow-hidden rounded-xl border border-indigo-100 bg-white">
                      <div className="grid grid-cols-4 gap-2 bg-slate-900 px-3 py-2 text-[10px] font-semibold text-white">
                        <span>{L("الدورة", "Course")}</span><span className="text-center">{L("المشتركين", "Subscribers")}</span><span className="text-center">{L("عمولة الفرد", "Per subscriber")}</span><span className="text-center">{L("الإجمالي", "Total")}</span>
                      </div>
                      <div className="divide-y divide-indigo-50">
                        {((inv.items?.length ? inv.items : [{ courseName: inv.courseName, subscriberCount: inv.subscriberCount, commissionPerSubscriber: inv.commissionPerSubscriber, totalCommission: inv.totalCommission }]) as any[]).map((item: any, idx: number) => (
                          <div key={`${inv.id}-course-${item.courseId ?? idx}`} className="grid grid-cols-4 gap-2 px-3 py-2 text-[11px] text-slate-700">
                            <span className="font-semibold text-slate-900">{item.courseName || "—"}</span>
                            <span className="text-center">{item.subscriberCount ?? 0}</span>
                            <span className="text-center">{item.commissionPerSubscriber ?? "0.00"}</span>
                            <span className="text-center font-bold text-indigo-700">{item.totalCommission ?? "0.00"}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
                    <div className="mb-3 rounded-2xl border border-amber-100 bg-amber-50 px-3 py-2 text-[11px] leading-5 text-amber-900">
                      <b>{L("تنبيه:", "Note:")}</b> {L("المبلغ المدفوع هو ما تم تحويله فعليًا، والخصم مستقل. المدفوع + الخصم لا يجب أن يتجاوز الإجمالي.", "Paid amount is what was actually transferred; deduction is separate. Paid + deduction cannot exceed total.")}
                    </div>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                      <div className="space-y-1">
                        <Label>{L("حالة الفاتورة", "Invoice status")}</Label>
                        <Select value={form.status} disabled={!canManage || isClosed} onValueChange={(v) => setField(inv.id, inv, "status", v)}>
                          <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                          <SelectContent><SelectItem value="Pending">{L("معلقة", "Pending")}</SelectItem><SelectItem value="Partial">{L("جزئية", "Partial")}</SelectItem><SelectItem value="Paid">{L("مدفوعة", "Paid")}</SelectItem></SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1">
                        <Label>{L("طريقة الصرف", "Payout method")}</Label>
                        <Select value={form.payoutMethod} disabled={!canManage || isClosed} onValueChange={(v) => setField(inv.id, inv, "payoutMethod", v)}>
                          <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                          <SelectContent><SelectItem value="BankTransfer">{L("تحويل بنكي", "Bank transfer")}</SelectItem><SelectItem value="Cash">{L("كاش", "Cash")}</SelectItem><SelectItem value="Other">{L("أخرى", "Other")}</SelectItem></SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1"><Label>{L("المبلغ المدفوع", "Paid amount")}</Label><Input disabled={!canManage || isClosed} value={form.paidAmount} onChange={(e) => setField(inv.id, inv, "paidAmount", e.target.value)} inputMode="decimal" /></div>
                      <div className="space-y-1"><Label>{L("رقم الحوالة", "Transfer reference")}</Label><Input disabled={!canManage || isClosed} value={form.transferReference} onChange={(e) => setField(inv.id, inv, "transferReference", e.target.value)} /></div>
                      <div className="space-y-1"><Label>{L("مبلغ الخصم", "Deduction")}</Label><Input disabled={!canManage || isClosed} value={form.deductionAmount} onChange={(e) => setField(inv.id, inv, "deductionAmount", e.target.value)} inputMode="decimal" /></div>
                      <div className="space-y-1"><Label>{L("سبب الخصم", "Deduction reason")}</Label><Input disabled={!canManage || isClosed} value={form.deductionReason} onChange={(e) => setField(inv.id, inv, "deductionReason", e.target.value)} /></div>
                      <div className="space-y-1"><Label>{L("موعد الصرف المتوقع", "Expected payment date")}</Label><Input type="date" disabled={!canManage || isClosed} value={form.expectedPaymentDate} onChange={(e) => setField(inv.id, inv, "expectedPaymentDate", e.target.value)} /></div>
                      <div className="space-y-1 md:col-span-2"><Label>{L("رابط إثبات الصرف", "Proof URL")}</Label><Input disabled={!canManage || isClosed} value={form.proofUrl} onChange={(e) => setField(inv.id, inv, "proofUrl", e.target.value)} placeholder="https://..." /></div>
                      <div className="space-y-1 md:col-span-2"><Label>{L("سبب التأخير", "Delay reason")}</Label><Input disabled={!canManage || isClosed} value={form.delayReason} onChange={(e) => setField(inv.id, inv, "delayReason", e.target.value)} /></div>
                      <div className="space-y-1 md:col-span-2"><Label>{L("ملاحظات الصرف", "Payout notes")}</Label><Input disabled={!canManage || isClosed} value={form.notes} onChange={(e) => setField(inv.id, inv, "notes", e.target.value)} /></div>
                    </div>
                  </div>

                  <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
                    <div className="flex items-center justify-between gap-2">
                      <div><p className="text-[12px] font-black">{L("جدول الدفعات المقسطة", "Payout schedule")}</p></div>
                      <Button size="sm" disabled={!canManage || isClosed} onClick={() => addScheduleRow(inv.id, inv)}>{L("إضافة دفعة", "Add payout")}</Button>
                    </div>
                    {(form.payoutSchedule ?? []).map((row: any, index: number) => (
                      <div key={index} className="rounded-2xl border border-slate-100 bg-slate-50/70 p-3">
                        <div className="mb-2 flex items-center justify-between"><p className="font-black">{L(`دفعة رقم ${index + 1}`, `Payout #${index + 1}`)}</p><Button size="sm" variant="outline" disabled={!canManage || isClosed} onClick={() => removeScheduleRow(inv.id, inv, index)} className="text-red-600">{L("حذف", "Remove")}</Button></div>
                        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
                          <div><Label>{L("المبلغ", "Amount")}</Label><Input disabled={!canManage || isClosed} value={row.amount} onChange={(e) => setScheduleField(inv.id, inv, index, "amount", e.target.value)} /></div>
                          <div><Label>{L("الاستحقاق", "Due date")}</Label><Input type="date" disabled={!canManage || isClosed} value={row.dueDate} onChange={(e) => setScheduleField(inv.id, inv, index, "dueDate", e.target.value)} /></div>
                          <div><Label>{L("تاريخ الدفع", "Paid at")}</Label><Input type="date" disabled={!canManage || isClosed} value={row.paidAt} onChange={(e) => setScheduleField(inv.id, inv, index, "paidAt", e.target.value)} /></div>
                          <div><Label>{L("رقم الحوالة", "Reference")}</Label><Input disabled={!canManage || isClosed} value={row.reference} onChange={(e) => setScheduleField(inv.id, inv, index, "reference", e.target.value)} /></div>
                          <div><Label>{L("ملاحظات", "Notes")}</Label><Input disabled={!canManage || isClosed} value={row.notes} onChange={(e) => setScheduleField(inv.id, inv, index, "notes", e.target.value)} /></div>
                        </div>
                      </div>
                    ))}
                    {(form.payoutSchedule ?? []).length === 0 && <p className="rounded-xl bg-slate-50 px-3 py-2 text-[11px] text-slate-500">{L("لا توجد دفعات مجدولة.", "No scheduled payouts.")}</p>}
                  </div>

                  <div className="flex justify-end">
                    <Button disabled={!canManage || isClosed || updateM.isPending} onClick={() => save(inv)} className="h-11 w-full rounded-2xl bg-gradient-to-r from-[#1e3a5f] to-[#6366f1] text-sm font-black text-white sm:w-auto sm:min-w-[220px]">
                      <WalletCards className="h-4 w-4" /> {L("حفظ تفاصيل الصرف", "Save payout details")}
                    </Button>
                  </div>
                </div>
              );
            })}

            {!invoicesQ.isLoading && invoices.length === 0 && <p className="p-4 text-sm text-slate-500">{L("لا توجد فواتير لهذا الشهر.", "No invoices for this month.")}</p>}
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
    changed.append("client/src/pages/affiliate/InvoicesPage.tsx")

app = APP.read_text(encoding="utf-8")
app0 = app
if 'import InvoicesPage from "./pages/affiliate/InvoicesPage";' not in app:
    anchors = [
        'import CommissionsPage from "./pages/affiliate/CommissionsPage";',
        'import SubscriptionsPage from "./pages/affiliate/SubscriptionsPage";',
        'import CoursesPage from "./pages/affiliate/CoursesPage";',
    ]
    for anchor in anchors:
        if anchor in app:
            app = app.replace(anchor, anchor + '\nimport InvoicesPage from "./pages/affiliate/InvoicesPage";', 1)
            break
    else:
        print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=APP_IMPORT_ANCHOR_NOT_FOUND")
        sys.exit(2)

if '<Route path="/affiliate-marketing/invoices" component={InvoicesPage} />' not in app:
    route = '      <Route path="/affiliate-marketing/invoices" component={InvoicesPage} />\n'
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
layout = layout.replace('{ section: "invoices",', '{ href: "/affiliate-marketing/invoices",')
if layout.count('href: "/affiliate-marketing/invoices"') < 2:
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=INVOICES_SIDEBAR_GUARD_FAILED")
    sys.exit(4)
if 'const href = sub.href || `/clients?setup=1&section=${sub.section}`;' not in layout:
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=SIDEBAR_HREF_MAPPER_MISSING")
    sys.exit(5)
if layout != layout0:
    backup(LAYOUT)
    LAYOUT.write_text(layout, encoding="utf-8")
    changed.append("client/src/components/CRMLayout.tsx")

final_app = APP.read_text(encoding="utf-8")
if final_app.find('/affiliate-marketing/invoices') > final_app.find('/affiliate-marketing/:tab'):
    print(f"PATCH={PATCH}\nAPPLY=FAIL\nERROR=ROUTE_ORDER_INVALID")
    sys.exit(6)

print(f"PATCH={PATCH}")
print("APPLY=PASS")
print("FILES=" + ";".join(changed))
print("ROUTE=/affiliate-marketing/invoices")
print("NO_DATA_ENTRY_MODAL=YES")
print("LEGACY_CLIENTPOOL=UNCHANGED")
print("BACKEND_DB_AUTH=UNCHANGED")
print("BUILD_REQUIRED=YES")
print("COMMIT=NO")
print("PUSH=NO")
