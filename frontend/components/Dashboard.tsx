"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { fetchJobs, fetchMetrics, Job, Metrics, reviewJob, submitInvoice } from "@/lib/api";

const WORKFLOW = [
  { key: "EXTRACTING", label: "Extracted" },
  { key: "CLASSIFIED", label: "Classified" },
  { key: "VALIDATED", label: "Validated" },
  { key: "HUMAN_REVIEW", label: "Human Review" }
] as const;

const STATUS_ORDER = [
  "CREATED",
  "EXTRACTING",
  "CLASSIFIED",
  "POLICY_IDENTIFIED",
  "VALIDATED",
  "REPORT_GENERATED",
  "HUMAN_REVIEW",
  "APPROVED",
  "REJECTED",
  "NEED_INFO",
  "FAILED"
];

function statusIndex(status: string) {
  return STATUS_ORDER.indexOf(status);
}

function isStepDone(job: Job, step: string) {
  if (job.status === "FAILED") return false;
  if (job.status === "NEED_INFO") return step !== "HUMAN_REVIEW";
  return statusIndex(job.status) >= statusIndex(step);
}

function labelValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "None";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedJob = useMemo(() => jobs.find((job) => job.id === selectedId) ?? jobs[0], [jobs, selectedId]);

  async function refresh() {
    const [jobData, metricData] = await Promise.all([fetchJobs(), fetchMetrics()]);
    setJobs(jobData);
    setMetrics(metricData);
    if (!selectedId && jobData.length > 0) setSelectedId(jobData[0].id);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
    const timer = window.setInterval(() => refresh().catch((err) => setError(err.message)), 5000);
    return () => window.clearInterval(timer);
  }, []);

  async function onUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const form = new FormData(event.currentTarget);
      await submitInvoice(form);
      event.currentTarget.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function onReview(action: "APPROVE" | "REJECT" | "REQUEST_MORE_INFO") {
    if (!selectedJob) return;
    setBusy(true);
    setError(null);
    try {
      await reviewJob(selectedJob.id, action);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setBusy(false);
    }
  }

  const chartData = metrics
    ? [
        { name: "Approved", value: metrics.approved },
        { name: "Rejected", value: metrics.rejected },
        { name: "Failed", value: metrics.failed },
        { name: "Pending", value: metrics.pending_reviews }
      ]
    : [];

  const validation = selectedJob?.validation_result ?? {};
  const policies = selectedJob?.policies_used ?? [];
  const report = selectedJob?.report ?? {};

  return (
    <main className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal text-ink">AIShippingInspectAgent</h1>
            <p className="mt-1 text-sm text-slate-600">Inspection operations dashboard</p>
          </div>
          <form onSubmit={onUpload} className="flex flex-wrap items-end gap-3">
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Region
              <input name="region" defaultValue="US" className="h-10 w-20 border border-line bg-white px-3 text-sm" />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Email
              <input
                name="submitter_email"
                placeholder="owner@example.com"
                className="h-10 w-48 border border-line bg-white px-3 text-sm"
              />
            </label>
            <label className="grid gap-1 text-xs font-medium text-slate-600">
              Invoice
              <input name="file" type="file" required className="h-10 w-64 border border-line bg-white px-3 py-2 text-sm" />
            </label>
            <button disabled={busy} className="h-10 bg-ink px-4 text-sm font-semibold text-white disabled:opacity-50">
              Upload Invoice
            </button>
          </form>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-5 px-6 py-6">
        {error && <div className="border border-alert bg-white px-4 py-3 text-sm font-medium text-alert">{error}</div>}

        <div className="grid gap-4 md:grid-cols-4">
          <MetricCard label="Total Requests" value={metrics?.total_requests ?? 0} />
          <MetricCard label="Approved" value={metrics?.approved ?? 0} tone="signal" />
          <MetricCard label="Rejected" value={metrics?.rejected ?? 0} tone="caution" />
          <MetricCard label="Failed" value={metrics?.failed ?? 0} tone="alert" />
        </div>

        <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <section className="border border-line bg-white">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Inspection Queue</h2>
              <span className="text-sm text-slate-500">{jobs.length} jobs</span>
            </div>
            <div className="divide-y divide-line">
              {jobs.map((job) => (
                <button
                  key={job.id}
                  onClick={() => setSelectedId(job.id)}
                  className={`grid w-full gap-3 px-4 py-4 text-left hover:bg-panel ${
                    selectedJob?.id === job.id ? "bg-panel" : "bg-white"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-ink">{job.file_name ?? job.id}</p>
                      <p className="mt-1 text-xs text-slate-500">{job.id}</p>
                    </div>
                    <StatusBadge status={job.status} />
                  </div>
                  <div className="grid gap-3 md:grid-cols-[150px_1fr]">
                    <div className="text-sm text-slate-600">{job.fleet_type ?? "Unclassified"}</div>
                    <WorkflowTracker job={job} />
                  </div>
                  <p className="line-clamp-2 text-sm text-slate-600">{String(reportSummary(job) ?? "Report pending")}</p>
                </button>
              ))}
              {jobs.length === 0 && <div className="px-4 py-12 text-center text-sm text-slate-500">No jobs submitted</div>}
            </div>
          </section>

          <aside className="grid gap-5">
            <section className="border border-line bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Dashboard Metrics</h2>
              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={chartData} dataKey="value" innerRadius={45} outerRadius={78} paddingAngle={2}>
                      {chartData.map((entry, index) => (
                        <Cell key={entry.name} fill={["#0f766e", "#b7791f", "#b42318", "#2563eb"][index]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-3 h-36">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={[{ name: "Pass", count: metrics?.pass_count ?? 0 }, { name: "Fail", count: metrics?.fail_count ?? 0 }]}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#2563eb" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            {selectedJob && (
              <section className="border border-line bg-white p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Inspector Panel</h2>
                    <p className="mt-1 text-sm text-slate-500">{selectedJob.file_name ?? selectedJob.id}</p>
                  </div>
                  <StatusBadge status={selectedJob.status} />
                </div>

                <div className="mt-4">
                  <WorkflowTracker job={selectedJob} />
                </div>

                <div className="mt-5 grid gap-3">
                  <DetailBlock title="Validation Details" value={validation} />
                  <DetailBlock title="Policies Used" value={policies} />
                  <DetailBlock title="Report Preview" value={report} />
                </div>

                {selectedJob.status === "FAILED" && (
                  <div className="mt-4 border border-alert bg-red-50 p-3 text-sm text-alert">
                    <p className="font-semibold">Root Cause</p>
                    <p className="mt-1">{selectedJob.error}</p>
                    <p className="mt-3 font-semibold">Required Documents</p>
                    <p className="mt-1">Corrected invoice, vehicle identification, applicable shipping evidence.</p>
                  </div>
                )}

                <div className="mt-5 grid grid-cols-3 gap-2">
                  <button
                    disabled={busy || selectedJob.status !== "HUMAN_REVIEW"}
                    onClick={() => onReview("APPROVE")}
                    className="h-10 bg-signal text-sm font-semibold text-white disabled:opacity-40"
                  >
                    Approve
                  </button>
                  <button
                    disabled={busy || selectedJob.status !== "HUMAN_REVIEW"}
                    onClick={() => onReview("REJECT")}
                    className="h-10 bg-alert text-sm font-semibold text-white disabled:opacity-40"
                  >
                    Reject
                  </button>
                  <button
                    disabled={busy || selectedJob.status !== "HUMAN_REVIEW"}
                    onClick={() => onReview("REQUEST_MORE_INFO")}
                    className="h-10 border border-line bg-white text-sm font-semibold text-ink disabled:opacity-40"
                  >
                    More Info
                  </button>
                </div>
              </section>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

function MetricCard({ label, value, tone = "ink" }: { label: string; value: number; tone?: "ink" | "signal" | "alert" | "caution" }) {
  const toneClass = {
    ink: "text-ink",
    signal: "text-signal",
    alert: "text-alert",
    caution: "text-caution"
  }[tone];

  return (
    <div className="border border-line bg-white px-4 py-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-2 text-3xl font-semibold tracking-normal ${toneClass}`}>{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const className =
    status === "APPROVED"
      ? "bg-emerald-50 text-signal"
      : status === "REJECTED" || status === "FAILED"
        ? "bg-red-50 text-alert"
        : status === "HUMAN_REVIEW" || status === "NEED_INFO"
          ? "bg-amber-50 text-caution"
          : "bg-blue-50 text-blue-700";

  return <span className={`px-2 py-1 text-xs font-semibold ${className}`}>{status.replaceAll("_", " ")}</span>;
}

function WorkflowTracker({ job }: { job: Job }) {
  return (
    <div className="grid grid-cols-4 gap-2">
      {WORKFLOW.map((step) => {
        const done = isStepDone(job, step.key);
        const active = job.status === step.key || (step.key === "HUMAN_REVIEW" && job.status === "NEED_INFO");
        return (
          <div key={step.key} className="min-w-0">
            <div className={`h-1.5 ${done ? "bg-signal" : active ? "bg-caution" : "bg-line"}`} />
            <p className="mt-1 truncate text-xs text-slate-600">{done ? "✓" : active ? "⏳" : "·"} {step.label}</p>
          </div>
        );
      })}
    </div>
  );
}

function DetailBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <details className="border border-line bg-panel p-3" open={title === "Validation Details"}>
      <summary className="cursor-pointer text-sm font-semibold text-ink">{title}</summary>
      <pre className="mt-3 max-h-56 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-700">{labelValue(value)}</pre>
    </details>
  );
}

function reportSummary(job: Job) {
  const report = job.report;
  if (!report || typeof report !== "object") return null;
  return report.summary ?? report.title ?? null;
}

