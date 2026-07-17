import type { ReactNode } from 'react';
import { DatabaseOutlined, ExperimentOutlined, LineChartOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { NavLink, useLocation } from 'react-router-dom';

const navigation = [
  { path: '/', label: '总览', icon: <LineChartOutlined /> },
  { path: '/setup', label: '新建模拟', icon: <PlayCircleOutlined /> },
  { path: '/data', label: '数据中心', icon: <DatabaseOutlined /> },
  { path: '/indicators', label: '指标工坊', icon: <ExperimentOutlined /> },
];

export default function TerminalShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const isTrading = location.pathname.startsWith('/trading/');

  return (
    <div className="terminal-shell">
      <header className="terminal-header">
        <div className="brand-block">
          <span className="brand-mark">RS</span>
          <div>
            <div className="brand-name">韭菜模拟器</div>
            <div className="brand-subtitle">A-SHARE DAILY LAB</div>
          </div>
        </div>
        <nav className="terminal-nav" aria-label="主导航">
          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              end={item.path === '/'}
            >
              {item.icon}<span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="market-status"><span className="status-dot" /> 本地日线模式</div>
      </header>
      <main className={isTrading ? 'terminal-main trading-main' : 'terminal-main'}>{children}</main>
    </div>
  );
}

