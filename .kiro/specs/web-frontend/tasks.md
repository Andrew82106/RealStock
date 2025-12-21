# Implementation Plan: Web 前端

## Overview

本实现计划将 Web 前端开发分为 4 个主要阶段：后端 API 开发、前端基础设施、核心组件开发和集成测试。

## Tasks

- [x] 1. 后端 API 服务
  - [x] 1.1 创建 FastAPI 项目结构
    - 创建 `api/` 目录结构
    - 创建 `api/main.py` FastAPI 应用入口
    - 配置 CORS 中间件
    - 添加依赖: fastapi, uvicorn, pydantic
    - _Requirements: 7.1-7.6_

  - [x] 1.2 实现股票数据 API
    - 创建 `api/routers/stocks.py`
    - 实现 GET /api/stocks 返回股票列表
    - 实现 GET /api/stocks/{code}/daily 返回日线数据
    - _Requirements: 7.1, 7.2_

  - [x] 1.3 实现游戏会话管理
    - 创建 `api/services/session.py` 管理游戏会话
    - 实现会话创建、获取、销毁
    - 使用内存存储会话（可扩展为 Redis）
    - _Requirements: 7.3_

  - [x] 1.4 实现游戏控制 API
    - 创建 `api/routers/game.py`
    - 实现 POST /api/game/start 开始游戏
    - 实现 POST /api/game/buy 买入
    - 实现 POST /api/game/sell 卖出
    - 实现 GET /api/game/{session_id}/account 获取账户
    - 实现 POST /api/game/{session_id}/next-day 下一交易日
    - _Requirements: 7.3, 7.4, 7.5_

  - [x] 1.5 实现 WebSocket 播放服务
    - 创建 `api/routers/websocket.py`
    - 实现 /ws/playback/{session_id} WebSocket 端点
    - 实现播放/暂停控制消息处理
    - 实现 tick 数据推送
    - _Requirements: 7.6_

- [x] 2. Checkpoint - 后端 API 完成
  - 使用 curl 或 Postman 测试所有 API 端点
  - 确保 WebSocket 连接正常

- [x] 3. 前端项目初始化
  - [x] 3.1 创建 React + TypeScript 项目
    - 使用 Vite 创建项目: `npm create vite@latest frontend -- --template react-ts`
    - 安装依赖: echarts, echarts-for-react, antd, axios
    - 配置 vite.config.ts 代理 API 请求
    - _Requirements: 前端基础设施_

  - [x] 3.2 创建类型定义和 API 服务
    - 创建 `frontend/src/types/index.ts` 定义所有类型
    - 创建 `frontend/src/services/api.ts` 封装 API 调用
    - 创建 `frontend/src/hooks/useWebSocket.ts` WebSocket Hook
    - _Requirements: 前端基础设施_

  - [x] 3.3 创建路由和页面结构
    - 安装 react-router-dom
    - 创建 GameSetup 页面（游戏设置）
    - 创建 TradingView 页面（交易主界面）
    - 配置路由
    - _Requirements: 6.1-6.4_

- [x] 4. 核心组件开发
  - [x] 4.1 实现 StockChart 组件
    - 使用 ECharts 绘制 K 线图
    - 支持日 K 线和分时图切换
    - 实现红涨绿跌颜色
    - 实现 tooltip 显示开高低收
    - _Requirements: 1.1-1.5_

  - [x] 4.2 实现 AccountPanel 组件
    - 显示总资产、可用现金、持仓市值
    - 显示收益率（相对初始资金）
    - 盈利红色、亏损绿色
    - _Requirements: 2.1, 2.4_

  - [x] 4.3 实现 PositionList 组件
    - 显示持仓列表表格
    - 包含代码、数量、成本、现价、盈亏
    - 实时更新价格和盈亏
    - _Requirements: 2.2, 2.3_

  - [x] 4.4 实现 TradingPanel 组件
    - 买入/卖出标签页切换
    - 价格和数量输入框
    - 显示预估费用
    - 提交按钮（非暂停状态禁用）
    - 显示订单结果
    - _Requirements: 3.1-3.5_

  - [x] 4.5 实现 PlaybackControl 组件
    - 播放/暂停按钮
    - 速度滑块 (1x-100x)
    - 当前日期和时间显示
    - 下一交易日按钮
    - _Requirements: 4.1-4.6_

  - [x] 4.6 实现 GameSetup 页面
    - 股票搜索和选择
    - 日期范围选择器
    - 初始资金输入
    - 开始游戏按钮
    - _Requirements: 6.1-6.4_

  - [x] 4.7 实现 TradingView 页面
    - 整合所有组件
    - 布局：左侧图表，右侧账户和交易面板
    - 底部播放控制
    - _Requirements: 整合_

- [x] 5. Checkpoint - 核心功能完成
  - 测试完整的游戏流程
  - 确保播放、暂停、交易功能正常

- [x] 6. 绩效报告和优化
  - [x] 6.1 实现 PerformanceReport 组件
    - 显示绩效指标卡片
    - 净值曲线图
    - 交易历史表格
    - 导出 CSV 按钮
    - _Requirements: 5.1-5.4_

  - [x] 6.2 实现响应式布局
    - 桌面端布局优化
    - 平板端适配
    - _Requirements: 8.1, 8.2_

- [x] 7. Final Checkpoint - 项目完成
  - 完整功能测试
  - 确保所有页面正常工作

## Notes

- 后端 API 使用 FastAPI，运行命令: `uvicorn api.main:app --reload`
- 前端使用 Vite，运行命令: `cd frontend && npm run dev`
- 开发时前端代理 API 请求到后端，生产环境需要配置 Nginx

