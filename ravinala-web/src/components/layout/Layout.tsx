import { Suspense } from "react";
import { Outlet } from "react-router-dom";
import MarketStrip from "./MarketStrip";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

function PageLoader() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "60vh",
        color: "#94A3B8",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 13,
        letterSpacing: "0.08em",
        gap: 10,
      }}
    >
      <span style={{ color: "#00D9FF", fontSize: 16 }}>⟳</span>
      Loading module…
    </div>
  );
}

export default function Layout() {
  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0A0E1A" }}>
      <Sidebar />
      <TopBar />
      <MarketStrip />
      <main
        style={{
          marginLeft: 280,
          minHeight: "100vh",
          padding: "110px 24px 24px 24px",
          boxSizing: "border-box",
          width: "calc(100vw - 280px)",
        }}
      >
        <Suspense fallback={<PageLoader />}>
          <Outlet />
        </Suspense>
      </main>
      <div className="watermark">RAVINALA</div>
    </div>
  );
}
