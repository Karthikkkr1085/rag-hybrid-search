import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Background } from "../components/Background";
import { AnalyticsAPI, Overview } from "../services/analytics";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from "recharts";

type Query = {
  query_id: string;
  session_id: string;
  timestamp?: string;
  query_text: string;
  provider: string;
  latency_ms: number;
  confidence_score?: number | null;
  success: boolean;
  error_message?: string | null;
  num_documents_retrieved: number;
};

function Card({
  title,
  value,
  color,
}: {
  title: string;
  value: string | number;
  color: string;
}) {
  return (

    <div className="glass-card analytics-card">
      <div
        style={{
          fontSize: 14,
          opacity: 0.7,
          marginBottom: 12,
        }}
      >
        {title}
      </div>

      <div
        style={{
          fontSize: 34,
          fontWeight: 700,
          color,
        }}
      >
        {value}
      </div>
    </div>
  );
}

export default function Analytics() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [recent, setRecent] = useState<Query[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const navigate = useNavigate();
  useEffect(() => {
    load();

    const timer = setInterval(load, 10000);

    return () => clearInterval(timer);
  }, []);

  async function load() {
    try {
      const overviewData = await AnalyticsAPI.getOverview();
      const recentData = await AnalyticsAPI.getRecent();

      setOverview(overviewData);
      setRecent(recentData.queries || []);
      setLastUpdated(new Date());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  const chartData = recent
    .slice(0, 10)
    .reverse()
    .map((item, index) => ({
      name: `${index + 1}`,
      latency: Math.round(item.latency_ms),
    }));

  const providerCounts = recent.reduce(
    (acc: Record<string, number>, item) => {
      acc[item.provider] = (acc[item.provider] || 0) + 1;
      return acc;
    },
    {}
  );

  const providerData = Object.entries(providerCounts).map(
    ([name, value]) => ({
      name,
      value,
    })
  );

  const COLORS = [
    "#60a5fa",
    "#4ade80",
    "#f59e0b",
    "#f472b6",
    "#a78bfa",
  ];

  if (loading) {
    return (
      <>
          <Background />

          <div
            className="section-shell"
            style={{
              paddingTop: "40px",
            }}
          >
          <div className="glass-card analytics-page">
            <h2>Loading analytics...</h2>
          </div>
        </div>
      </>
    );
  }

  if (!overview) {
    return (
      <>
        <Background />

        <div className="section-shell">
          <div className="glass-card analytics-page">
            <h2>Failed to load analytics.</h2>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Background />

      <div className="section-shell">

        <div className="analytics-header">

          <div>
          <h1
            style={{
              fontSize: "clamp(2.5rem, 4vw, 4.5rem)",
              fontWeight: 800,
              margin: 0,
              lineHeight: 1.1,
            }}
          >
            📊 Analytics Dashboard
          </h1>

            <p>
              Monitor your Hybrid RAG system in real time.
            </p>
          </div>

          <div className="analytics-actions">
              <button
                  className="button button-secondary"
                  onClick={() => navigate("/")}
              >
                  ← Back
              </button>

              <button
                  className="button button-primary"
                  onClick={load}
              >
                  🔄 Refresh
              </button>
          </div>

        </div>

        <div className="analytics-grid">

          <Card
            title="Total Queries"
            value={overview.total_queries}
            color="#60a5fa"
          />

          <Card
            title="Success Rate"
            value={`${overview.success_rate}%`}
            color="#4ade80"
          />

          <Card
            title="Average Response"
            value={`${Math.round(
              overview.avg_response_time_ms
            )} ms`}
            color="#f59e0b"
          />

          <Card
            title="Confidence"
            value={overview.avg_confidence_score.toFixed(2)}
            color="#f472b6"
          />

          <Card
            title="Sessions"
            value={overview.total_sessions}
            color="#a78bfa"
          />

          <Card
            title="Documents"
            value={overview.total_documents_referenced}
            color="#38bdf8"
          />

          <Card
            title="Last Updated"
            value={
              lastUpdated
                ? lastUpdated.toLocaleTimeString()
                : "-"
            }
            color="#22d3ee"
          />

        </div>

        <div className="analytics-chart-grid">

          <div className="glass-card chart-card">

            <h2>📈 Query Trend</h2>

            <ResponsiveContainer width="100%" height={280}>

              <LineChart data={chartData}>

                <CartesianGrid strokeDasharray="3 3" />

                <XAxis dataKey="name" />

                <YAxis />

                <Tooltip />

                <Line
                  type="monotone"
                  dataKey="latency"
                  stroke="#60a5fa"
                  strokeWidth={3}
                />

              </LineChart>

            </ResponsiveContainer>

          </div>
                    <div className="glass-card chart-card">

                    <h2>🥧 Provider Distribution</h2>

                    <ResponsiveContainer width="100%" height={280}>

                    <PieChart>

                        <Pie
                        data={providerData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={({ percent }) =>
                            `${((percent ?? 0) * 100).toFixed(0)}%`
                        }
                        >

                        {providerData.map((_, index) => (

                            <Cell
                            key={index}
                            fill={COLORS[index % COLORS.length]}
                            />

                        ))}

                        </Pie>

                        <Tooltip />

                    </PieChart>

                    </ResponsiveContainer>

                </div>

                </div>

                <div className="glass-card analytics-table-card">

                <h2>📋 Recent Queries</h2>

                <table className="analytics-table">

                    <thead>

                    <tr>

                        <th style={th}>Query</th>

                        <th style={th}>Provider</th>

                        <th style={th}>Latency</th>

                        <th style={th}>Status</th>

                        <th style={th}>Time</th>

                        <th style={th}>Confidence</th>
                    </tr>

                    </thead>

                    <tbody>

                    {recent.length === 0 ? (

                        <tr>

                        <td
                            colSpan={5}
                            style={{
                            textAlign: "center",
                            padding: "30px",
                            opacity: 0.7,
                            }}
                        >
                            No queries recorded yet.
                        </td>

                        </tr>

                    ) : (

                        recent.map((q, index) => (

                        <tr key={index}>

                            <td style={td}>
                            {q.query_text}
                            </td>

                            <td style={td}>
                            {q.provider}
                            </td>

                            <td style={td}>
                            {Math.round(q.latency_ms)} ms
                            </td>

                            <td style={td}>

                            <span
                                style={{
                                color: q.success
                                    ? "#22c55e"
                                    : "#ef4444",
                                fontWeight: 600,
                                }}
                            >
                                {q.success
                                ? "🟢 Success"
                                : "🔴 Failed"}
                            </span>

                            </td>

                            <td style={td}>
                              {q.timestamp
                                ? new Date(q.timestamp).toLocaleString()
                                : "-"}
                            </td>
                            <td style={td}>
                              {q.confidence_score != null
                                ? `${(q.confidence_score * 100).toFixed(1)}%`
                                : "-"}
                            </td>
                        </tr>
                        
                        ))

                    )}

                    </tbody>

                </table>

                </div>

            </div>

            </>
        );
        }

        const th: React.CSSProperties = {
        padding: "16px",
        textAlign: "left",
        fontWeight: 600,
        borderBottom:
            "1px solid rgba(255,255,255,.08)",
        };

        const td: React.CSSProperties = {
        padding: "14px",
        borderBottom:
            "1px solid rgba(255,255,255,.06)",
        };