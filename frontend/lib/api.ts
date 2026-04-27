export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type JobStatus =
  | "CREATED"
  | "EXTRACTING"
  | "CLASSIFIED"
  | "POLICY_IDENTIFIED"
  | "VALIDATED"
  | "REPORT_GENERATED"
  | "HUMAN_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "NEED_INFO"
  | "FAILED";

export type Job = {
  id: string;
  status: JobStatus;
  fleet_type: string | null;
  region: string;
  file_name: string | null;
  policies_used: Array<Record<string, unknown>> | null;
  validation_result: Record<string, unknown> | null;
  report: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type Metrics = {
  total_requests: number;
  approved: number;
  rejected: number;
  failed: number;
  pending_reviews: number;
  pass_count: number;
  fail_count: number;
  failure_reasons: Array<{ reason: string; count: number }>;
};

export async function fetchJobs(): Promise<Job[]> {
  const response = await fetch(`${API_BASE}/jobs`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load jobs");
  return response.json();
}

export async function fetchMetrics(): Promise<Metrics> {
  const response = await fetch(`${API_BASE}/metrics`, { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load metrics");
  return response.json();
}

export async function reviewJob(jobId: string, action: "APPROVE" | "REJECT" | "REQUEST_MORE_INFO") {
  const response = await fetch(`${API_BASE}/review/${jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action })
  });
  if (!response.ok) throw new Error("Review action failed");
  return response.json();
}

export async function submitInvoice(formData: FormData) {
  const response = await fetch(`${API_BASE}/submit`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) throw new Error("Upload failed");
  return response.json();
}

