/**
 * A股模拟交易系统 - 主应用
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Spin, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { lazy, Suspense } from 'react';
import TerminalShell from './components/TerminalShell';

const HomePage = lazy(() => import('./pages/HomePage'));
const GameSetup = lazy(() => import('./pages/GameSetup'));
const TradingView = lazy(() => import('./pages/TradingView'));
const DataCenter = lazy(() => import('./pages/DataCenter'));
const IndicatorLab = lazy(() => import('./pages/IndicatorLab'));

function App() {
  return (
    <ConfigProvider 
      locale={zhCN}
      theme={{
        algorithm: antdTheme.darkAlgorithm,
        token: {
          colorPrimary: '#d6aa48',
          colorInfo: '#d6aa48',
          colorSuccess: '#d85151',
          colorError: '#1ca678',
          colorBgBase: '#090d12',
          colorBgContainer: '#111821',
          colorBorder: '#26313d',
          borderRadius: 2,
          fontFamily: "Inter, 'Segoe UI', 'Microsoft YaHei', sans-serif",
        },
        components: {
          Button: { controlHeight: 36, fontWeight: 600 },
          Card: { headerBg: '#111821' },
          Table: { headerBg: '#0c1219', rowHoverBg: '#17212b' },
        },
      }}
    >
      <BrowserRouter>
        <TerminalShell>
          <Suspense fallback={<div className="route-loading"><Spin /><span>正在加载工作区</span></div>}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/setup" element={<GameSetup />} />
              <Route path="/data" element={<DataCenter />} />
              <Route path="/indicators" element={<IndicatorLab />} />
              <Route path="/trading/:sessionId" element={<TradingView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </TerminalShell>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
