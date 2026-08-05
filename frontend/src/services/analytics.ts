const API_BASE = "http://127.0.0.1:8000";

export interface Overview {
  period_days: number;
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  success_rate: number;
  avg_response_time_ms: number;
  avg_confidence_score: number;
  total_sessions: number;
  total_documents_referenced: number;
}

export interface RecentQuery {
  id?: number;
  session_id: string;
  query_text: string;
  provider: string;
  latency_ms: number;
  success: boolean;
  created_at: string;
}

export interface RecentQueriesResponse {
  queries: RecentQuery[];
  limit: number;
  offset: number;
}

async function request<T>(url: string): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`);

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

export const AnalyticsAPI = {
  getOverview() {
    return request<Overview>("/analytics/overview");
  },

  getRecent() {
    return request<RecentQueriesResponse>("/analytics/recent");
  },

  getProviders() {
    return request<any>("/analytics/providers");
  },

  getPerformance() {
    return request<any>("/analytics/performance");
  },

  getConfidence() {
    return request<any>("/analytics/confidence");
  },

  getDocuments() {
    return request<any>("/analytics/documents");
  }
};