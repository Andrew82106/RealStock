# Requirements Document

## Introduction

A 股模拟交易回测系统的 Web 前端界面，提供游戏化的交易体验。用户可以通过浏览器查看股票行情、进行模拟交易、观看日内行情播放，并查看交易绩效报告。

## Glossary

- **Web_Frontend**: Web 前端应用，基于 React 构建的单页应用
- **API_Server**: 后端 API 服务，基于 FastAPI 提供 RESTful 接口
- **Chart_Component**: K线图组件，用于展示股票价格走势
- **Trading_Panel**: 交易面板，用于提交买入/卖出订单
- **Playback_Control**: 播放控制组件，用于控制日内行情播放
- **WebSocket**: 实时通信协议，用于推送行情数据更新

## Requirements

### Requirement 1: 股票行情展示

**User Story:** As a 用户, I want to 在网页上查看股票的K线图和分时图, so that 我可以分析行情走势做出交易决策。

#### Acceptance Criteria

1. WHEN 用户选择一只股票 THEN THE Web_Frontend SHALL 显示该股票的日K线图
2. WHEN 用户切换到分时视图 THEN THE Web_Frontend SHALL 显示当日的分时走势图
3. THE Chart_Component SHALL 支持缩放和拖拽查看历史数据
4. WHEN 鼠标悬停在K线上 THEN THE Chart_Component SHALL 显示该日的开高低收和成交量
5. THE Chart_Component SHALL 使用红色表示上涨、绿色表示下跌（符合A股习惯）

### Requirement 2: 账户信息展示

**User Story:** As a 用户, I want to 实时查看我的账户状态, so that 我可以了解资金和持仓情况。

#### Acceptance Criteria

1. THE Web_Frontend SHALL 在页面顶部显示总资产、可用现金和持仓市值
2. THE Web_Frontend SHALL 显示持仓列表，包含股票代码、数量、成本价、现价和盈亏
3. WHEN 行情更新 THEN THE Web_Frontend SHALL 实时更新持仓的浮动盈亏
4. THE Web_Frontend SHALL 用颜色区分盈利（红色）和亏损（绿色）

### Requirement 3: 交易操作

**User Story:** As a 用户, I want to 通过网页界面进行买入和卖出操作, so that 我可以方便地进行模拟交易。

#### Acceptance Criteria

1. WHEN 用户点击买入按钮 THEN THE Trading_Panel SHALL 显示买入表单
2. THE Trading_Panel SHALL 允许用户输入委托价格和数量
3. WHEN 用户提交订单 THEN THE Web_Frontend SHALL 显示订单执行结果（成功或失败原因）
4. IF 订单被拒绝 THEN THE Web_Frontend SHALL 显示具体的拒绝原因
5. THE Trading_Panel SHALL 显示预估的交易费用

### Requirement 4: 日内行情播放控制

**User Story:** As a 用户, I want to 控制日内行情的播放速度和暂停, so that 我可以像玩游戏一样体验交易。

#### Acceptance Criteria

1. THE Playback_Control SHALL 提供播放/暂停按钮
2. THE Playback_Control SHALL 提供速度调节滑块（1x-100x）
3. WHEN 用户点击播放 THEN THE Web_Frontend SHALL 开始推进行情时间
4. WHEN 用户点击暂停 THEN THE Web_Frontend SHALL 停止行情推进并允许交易
5. THE Playback_Control SHALL 显示当前的模拟时间（日期和时间）
6. WHEN 当日行情播放完毕 THEN THE Web_Frontend SHALL 显示"下一交易日"按钮

### Requirement 5: 绩效报告展示

**User Story:** As a 用户, I want to 查看我的交易绩效报告, so that 我可以评估自己的交易表现。

#### Acceptance Criteria

1. THE Web_Frontend SHALL 显示总收益率、最大回撤、胜率和夏普比率
2. THE Web_Frontend SHALL 显示净值曲线图
3. THE Web_Frontend SHALL 显示交易历史列表
4. WHEN 用户点击导出 THEN THE Web_Frontend SHALL 下载交易日志CSV文件

### Requirement 6: 游戏初始化

**User Story:** As a 用户, I want to 设置游戏参数开始新游戏, so that 我可以自定义模拟交易的条件。

#### Acceptance Criteria

1. THE Web_Frontend SHALL 提供股票选择界面，支持搜索和多选
2. THE Web_Frontend SHALL 提供日期范围选择器
3. THE Web_Frontend SHALL 提供初始资金输入框（默认10万）
4. WHEN 用户点击开始游戏 THEN THE Web_Frontend SHALL 初始化模拟器并进入交易界面

### Requirement 7: API 服务

**User Story:** As a 前端开发者, I want to 通过 RESTful API 与后端交互, so that 前端可以获取数据和执行操作。

#### Acceptance Criteria

1. THE API_Server SHALL 提供 GET /api/stocks 返回股票列表
2. THE API_Server SHALL 提供 GET /api/stocks/{code}/daily 返回日线数据
3. THE API_Server SHALL 提供 POST /api/game/start 初始化游戏
4. THE API_Server SHALL 提供 POST /api/game/buy 执行买入
5. THE API_Server SHALL 提供 POST /api/game/sell 执行卖出
6. THE API_Server SHALL 提供 WebSocket /ws/playback 推送实时行情

### Requirement 8: 响应式设计

**User Story:** As a 用户, I want to 在不同设备上使用系统, so that 我可以随时随地进行模拟交易。

#### Acceptance Criteria

1. THE Web_Frontend SHALL 适配桌面浏览器（1920x1080 及以上）
2. THE Web_Frontend SHALL 适配平板设备（768px-1024px）
3. THE Web_Frontend SHALL 在移动设备上提供基本功能（查看行情和账户）

