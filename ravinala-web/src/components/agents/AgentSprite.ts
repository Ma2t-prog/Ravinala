/**
 * Agent sprite constants — positions, colors, and type definitions.
 */

export const AGENT_POSITIONS: Record<string, { x: number; y: number; zone: string }> = {
  OrchestratorAgent: { x: 420, y: 100, zone: 'center' },
  MarketAgent:       { x: 125, y: 100, zone: 'market' },
  AnalysisAgent:     { x: 125, y: 255, zone: 'analysis' },
  RiskAgent:         { x: 715, y: 100, zone: 'risk' },
  PortfolioAgent:    { x: 420, y: 255, zone: 'portfolio' },
  BacktestAgent:     { x: 715, y: 255, zone: 'backtest' },
  MLAgent:           { x: 420, y: 410, zone: 'ml' },
  MonitoringAgent:   { x: 125, y: 410, zone: 'monitoring' },
  ErrorHandlerAgent: { x: 565, y: 410, zone: 'error' },
  LoggerAgent:       { x: 715, y: 410, zone: 'logger' },
  ReportAgent:       { x: 955, y: 348, zone: 'archive' },
  AlertAgent:        { x: 955, y: 512, zone: 'alert' },
};

export const AGENT_COLORS: Record<string, string> = {
  OrchestratorAgent: '#D4AF37',
  MarketAgent:       '#00D4FF',
  AnalysisAgent:     '#3B82F6',
  RiskAgent:         '#EF4444',
  PortfolioAgent:    '#10B981',
  BacktestAgent:     '#F59E0B',
  MLAgent:           '#8B5CF6',
  MonitoringAgent:   '#6366F1',
  ErrorHandlerAgent: '#F43F5E',
  LoggerAgent:       '#94A3B8',
  ReportAgent:       '#A78BFA',
  AlertAgent:        '#FB923C',
};
