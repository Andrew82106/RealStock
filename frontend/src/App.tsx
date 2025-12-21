/**
 * A股模拟交易系统 - 主应用
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import HomePage from './pages/HomePage';
import GameSetup from './pages/GameSetup';
import TradingView from './pages/TradingView';

function AppContent() {
  const { theme } = useTheme();
  
  // 设置全局背景色
  const bgColor = theme === 'dark' ? '#0d1117' : '#f0f2f5';
  
  return (
    <ConfigProvider 
      locale={zhCN}
      theme={{
        algorithm: theme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      }}
    >
      <div style={{ minHeight: '100vh', background: bgColor }}>
        <BrowserRouter>
          <Routes>
            {/* 主页 - 存档列表 (Requirements: 1.4) */}
            <Route path="/" element={<HomePage />} />
            {/* 旧版游戏设置页面 - 保留兼容性 */}
            <Route path="/setup" element={<GameSetup />} />
            {/* 交易页面 - 支持存档ID和会话ID */}
            <Route path="/trading/:sessionId" element={<TradingView />} />
            {/* 默认重定向到主页 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </div>
    </ConfigProvider>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
