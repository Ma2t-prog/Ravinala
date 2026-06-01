import { useState } from "react";
import { exportExcel, exportPDF } from "../../api/market";
import { Badge, Card } from "../../components/ui";
import { useSnapshot } from "../../hooks/useMarketData";

const TEMPLATES = [
  {
    id: "reg",
    name: "Regulatory Report",
    description:
      "Basel III/IV capital adequacy, liquidity ratios, and risk metrics for regulatory submission",
    icon: "&#9878;",
  },
  {
    id: "client",
    name: "Client Report",
    description:
      "Portfolio performance, attribution analysis, and market commentary for client distribution",
    icon: "&#128200;",
  },
  {
    id: "internal",
    name: "Internal Risk Report",
    description:
      "Comprehensive risk dashboard, VaR analysis, stress testing, and limit monitoring",
    icon: "&#128202;",
  },
];

const RECENT_REPORTS = [
  {
    name: "Q4 2025 Regulatory Capital Report",
    template: "Regulatory",
    date: "2026-01-15",
    status: "Completed",
    pages: 42,
    format: "PDF",
  },
  {
    name: "Feb 2026 Client Portfolio Review",
    template: "Client",
    date: "2026-03-01",
    status: "Completed",
    pages: 28,
    format: "PDF",
  },
  {
    name: "Weekly Risk Dashboard W11",
    template: "Internal",
    date: "2026-03-15",
    status: "Completed",
    pages: 15,
    format: "XLSX",
  },
  {
    name: "Stress Test Results Q1 2026",
    template: "Internal",
    date: "2026-03-18",
    status: "Completed",
    pages: 22,
    format: "PDF",
  },
  {
    name: "Mar 2026 Client Monthly Statement",
    template: "Client",
    date: "2026-03-20",
    status: "Processing",
    pages: 0,
    format: "PDF",
  },
  {
    name: "COREP Submission Q1 2026",
    template: "Regulatory",
    date: "2026-03-22",
    status: "Draft",
    pages: 0,
    format: "XML",
  },
];

export default function ReportGenerator() {
  const { data: snapshotData } = useSnapshot();
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [reportName, setReportName] = useState("");
  const [dateFrom, setDateFrom] = useState("2026-01-01");
  const [dateTo, setDateTo] = useState("2026-03-22");
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!selectedTemplate) return;
    setGenerating(true);
    setGenerateError(null);
    try {
      // Internal risk report uses Excel; regulatory and client reports use PDF
      if (selectedTemplate === "internal") {
        const blob = await exportExcel([
          "indices",
          "bonds",
          "fx",
          "commodities",
        ]);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportName || "report"}_${new Date().toISOString().slice(0, 10)}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const blob = await exportPDF();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportName || "report"}_${new Date().toISOString().slice(0, 10)}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {
      setGenerateError("Report generation failed — check backend is running");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div style={{ color: "#F1F5F9" }}>
      {!snapshotData && (
        <div
          style={{
            background: "rgba(245,158,11,0.15)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 8,
            padding: "8px 16px",
            marginBottom: 16,
            fontSize: 13,
            color: "#F59E0B",
            fontFamily: "Inter, sans-serif",
          }}
        >
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 4,
        }}
      >
        Report Generator
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 20, fontSize: 14 }}>
        Generate regulatory, client & internal reports
        {snapshotData?.timestamp && (
          <span style={{ marginLeft: 12, fontSize: 12, color: "#64748B" }}>
            · Live data as of{" "}
            {new Date(snapshotData.timestamp).toLocaleTimeString()}
          </span>
        )}
      </p>

      {/* Template selector */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 12,
          marginBottom: 20,
        }}
      >
        {TEMPLATES.map((t) => (
          <div
            key={t.id}
            onClick={() => setSelectedTemplate(t.id)}
            style={{
              backgroundColor: "#131823",
              borderRadius: 10,
              padding: 16,
              cursor: "pointer",
              border: `2px solid ${selectedTemplate === t.id ? "#00D9FF" : "rgba(51,65,85,0.3)"}`,
              transition: "border-color 0.2s",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 8,
              }}
            >
              <span
                style={{ fontSize: 20 }}
                dangerouslySetInnerHTML={{ __html: t.icon }}
              />
              <span
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: selectedTemplate === t.id ? "#00D9FF" : "#F1F5F9",
                }}
              >
                {t.name}
              </span>
            </div>
            <p style={{ color: "#94A3B8", fontSize: 12, lineHeight: 1.4 }}>
              {t.description}
            </p>
          </div>
        ))}
      </div>

      {/* Parameters */}
      {selectedTemplate && (
        <Card title="Report Parameters" className="mb-4">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: 16,
            }}
          >
            <div>
              <label
                style={{
                  fontSize: 12,
                  color: "#94A3B8",
                  display: "block",
                  marginBottom: 4,
                }}
              >
                Report Name
              </label>
              <input
                type="text"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                placeholder="Enter report name..."
                style={{
                  width: "100%",
                  backgroundColor: "#0A0E1A",
                  border: "1px solid rgba(51,65,85,0.5)",
                  borderRadius: 6,
                  color: "#F1F5F9",
                  padding: "8px 10px",
                  fontSize: 13,
                  outline: "none",
                }}
              />
            </div>
            <div>
              <label
                style={{
                  fontSize: 12,
                  color: "#94A3B8",
                  display: "block",
                  marginBottom: 4,
                }}
              >
                Period From
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                style={{
                  width: "100%",
                  backgroundColor: "#0A0E1A",
                  border: "1px solid rgba(51,65,85,0.5)",
                  borderRadius: 6,
                  color: "#F1F5F9",
                  padding: "8px 10px",
                  fontSize: 13,
                  outline: "none",
                }}
              />
            </div>
            <div>
              <label
                style={{
                  fontSize: 12,
                  color: "#94A3B8",
                  display: "block",
                  marginBottom: 4,
                }}
              >
                Period To
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                style={{
                  width: "100%",
                  backgroundColor: "#0A0E1A",
                  border: "1px solid rgba(51,65,85,0.5)",
                  borderRadius: 6,
                  color: "#F1F5F9",
                  padding: "8px 10px",
                  fontSize: 13,
                  outline: "none",
                }}
              />
            </div>
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button
                onClick={handleGenerate}
                disabled={generating || !selectedTemplate}
                style={{
                  backgroundColor: "#00D9FF",
                  color: "#0A0E1A",
                  border: "none",
                  borderRadius: 8,
                  padding: "10px 24px",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor:
                    generating || !selectedTemplate ? "not-allowed" : "pointer",
                  opacity: generating || !selectedTemplate ? 0.6 : 1,
                  width: "100%",
                }}
              >
                {generating ? "Generating..." : "Generate Report"}
              </button>
              {generateError && (
                <p style={{ color: "#EF4444", fontSize: 12, marginTop: 6 }}>
                  {generateError}
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Recent Reports */}
      <Card title="Recent Reports" subtitle="Previously generated reports">
        <div style={{ overflowX: "auto" }}>
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                {[
                  "Report Name",
                  "Template",
                  "Date",
                  "Pages",
                  "Format",
                  "Status",
                ].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "8px 10px",
                      textAlign: "left",
                      color: "#94A3B8",
                      fontWeight: 500,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {RECENT_REPORTS.map((r, i) => (
                <tr
                  key={i}
                  style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                >
                  <td style={{ padding: "8px 10px", color: "#F1F5F9" }}>
                    {r.name}
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <Badge variant="info">{r.template}</Badge>
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#94A3B8",
                      fontSize: 12,
                    }}
                  >
                    {r.date}
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#94A3B8",
                    }}
                  >
                    {r.pages || "-"}
                  </td>
                  <td style={{ padding: "8px 10px", color: "#64748B" }}>
                    {r.format}
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <Badge
                      variant={
                        r.status === "Completed"
                          ? "up"
                          : r.status === "Processing"
                            ? "warning"
                            : "neutral"
                      }
                    >
                      {r.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
