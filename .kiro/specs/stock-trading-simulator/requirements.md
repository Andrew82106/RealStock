# Requirements Document

## Introduction

基于 AkShare 的 A 股模拟交易回测系统，允许用户在历史行情中进行"穿越式"交易，或在当前行情下进行模拟操作。通过真实的 A 股历史数据，验证用户自定义交易策略的有效性。

## Glossary

- **Data_Engine**: 数据准备模块，负责从 AkShare 获取股票数据并进行缓存管理
- **Account_System**: 虚拟账户模块，管理用户资金、持仓和交易费用
- **Trading_Engine**: 交易引擎模块，处理买卖逻辑和成交验证
- **Game_Loop**: 游戏/回测流程控制模块，管理时间推进和策略执行
- **Playback_Mode**: 行情播放模式，用户可以设定速度播放日内行情
- **Intraday_Data**: 日内分时数据，包含每分钟的价格和成交量
- **Position**: 持仓记录，包含股票代码、数量、成本价等信息
- **Forward_Adjustment**: 前复权，调整历史价格以消除除权除息造成的价格跳空
- **T_Plus_1**: T+1 交易制度，当天买入的股票当天不能卖出

## Requirements

### Requirement 1: 股票数据获取

**User Story:** As a 用户, I want to 获取 A 股股票的历史行情数据, so that 我可以基于真实数据进行模拟交易。

#### Acceptance Criteria

1. WHEN 用户请求股票列表 THEN THE Data_Engine SHALL 返回所有正常上市的 A 股股票代码和名称
2. WHEN 用户指定股票代码、起始日期和结束日期 THEN THE Data_Engine SHALL 返回该股票的日线数据，包含开盘价、最高价、最低价、收盘价和成交量
3. THE Data_Engine SHALL 默认返回前复权数据以确保历史价格的连续性
4. WHEN 数据已存在于本地缓存 THEN THE Data_Engine SHALL 从缓存读取数据而非调用 API
5. WHEN 数据不存在于本地缓存 THEN THE Data_Engine SHALL 从 AkShare 下载数据并保存到本地缓存

### Requirement 2: 虚拟账户管理

**User Story:** As a 用户, I want to 拥有一个虚拟交易账户, so that 我可以管理我的模拟资金和持仓。

#### Acceptance Criteria

1. WHEN 创建新账户 THEN THE Account_System SHALL 初始化指定金额的可用现金（默认 100,000 RMB）
2. THE Account_System SHALL 维护可用现金余额
3. THE Account_System SHALL 维护持仓列表，每个持仓包含股票代码、持仓数量、买入成本价、当前价和浮动盈亏
4. WHEN 查询总资产 THEN THE Account_System SHALL 返回可用现金加上所有持仓市值的总和
5. WHEN 执行卖出交易 THEN THE Account_System SHALL 收取 0.05% 的印花税
6. WHEN 执行买入或卖出交易 THEN THE Account_System SHALL 收取 0.025% 的佣金，最低 5 元

### Requirement 3: 买入交易

**User Story:** As a 用户, I want to 买入股票, so that 我可以建立持仓。

#### Acceptance Criteria

1. WHEN 用户提交买入订单 THEN THE Trading_Engine SHALL 验证可用现金是否足够支付股票金额和交易费用
2. IF 可用现金不足 THEN THE Trading_Engine SHALL 拒绝订单并返回错误信息
3. WHEN 买入订单成功执行 THEN THE Trading_Engine SHALL 扣减可用现金并增加持仓
4. WHEN 在回测模式下执行买入 THEN THE Trading_Engine SHALL 验证委托价格是否在当天最低价和最高价范围内
5. IF 委托价格超出当天价格范围 THEN THE Trading_Engine SHALL 拒绝订单

### Requirement 4: 卖出交易

**User Story:** As a 用户, I want to 卖出股票, so that 我可以实现盈利或止损。

#### Acceptance Criteria

1. WHEN 用户提交卖出订单 THEN THE Trading_Engine SHALL 验证持仓数量是否足够
2. IF 持仓数量不足 THEN THE Trading_Engine SHALL 拒绝订单并返回错误信息
3. WHEN 卖出订单成功执行 THEN THE Trading_Engine SHALL 增加可用现金并减少持仓
4. WHEN 在回测模式下执行卖出 THEN THE Trading_Engine SHALL 验证委托价格是否在当天最低价和最高价范围内
5. IF 委托价格超出当天价格范围 THEN THE Trading_Engine SHALL 拒绝订单

### Requirement 5: T+1 交易限制

**User Story:** As a 用户, I want to 系统遵守 A 股 T+1 规则, so that 模拟交易更接近真实市场。

#### Acceptance Criteria

1. WHEN 用户当天买入股票 THEN THE Trading_Engine SHALL 标记该持仓为当天不可卖出
2. IF 用户尝试卖出当天买入的股票 THEN THE Trading_Engine SHALL 拒绝订单并返回 T+1 限制错误
3. WHEN 游戏日期推进到下一天 THEN THE Trading_Engine SHALL 解除前一天买入股票的卖出限制

### Requirement 6: 日内行情播放模式

**User Story:** As a 用户, I want to 以可控速度播放日内行情, so that 我可以观察行情走势并在合适时机做出交易决策。

#### Acceptance Criteria

1. WHEN 用户选定开始日期并点击播放按钮 THEN THE Game_Loop SHALL 从该日开盘时刻开始播放行情
2. WHEN 行情播放中 THEN THE Game_Loop SHALL 按用户设定的速度逐步更新价格、成交量和换手率数据
3. WHEN 用户点击暂停按钮 THEN THE Game_Loop SHALL 暂停行情播放并允许用户进行买入或卖出操作
4. WHEN 当日行情播放完毕（收盘） THEN THE Game_Loop SHALL 自动停止并显示当日交易汇总
5. WHEN 当日结束后 THEN THE Game_Loop SHALL 提供"开始下一交易日"按钮
6. WHEN 用户点击"开始下一交易日" THEN THE Game_Loop SHALL 从下一交易日开盘时刻开始，等待用户点击播放
7. WHEN 行情播放中 THEN THE Game_Loop SHALL 实时更新所有持仓的当前价格和浮动盈亏
8. WHEN 到达数据的最后一个交易日收盘 THEN THE Game_Loop SHALL 结束游戏并显示最终绩效报告

### Requirement 10: 日内分时数据获取

**User Story:** As a 用户, I want to 获取股票的日内分时数据, so that 我可以观察更细粒度的行情走势。

#### Acceptance Criteria

1. WHEN 用户指定股票代码和日期 THEN THE Data_Engine SHALL 返回该股票当日的分时数据
2. THE Data_Engine SHALL 返回的分时数据包含时间、价格、成交量、换手率
3. WHEN 分时数据已存在于本地缓存 THEN THE Data_Engine SHALL 从缓存读取
4. IF 分时数据不可用 THEN THE Data_Engine SHALL 基于日线数据模拟生成分时走势

### Requirement 7: 自动回测模式

**User Story:** As a 用户, I want to 自动运行交易策略, so that 我可以快速验证策略在历史数据上的表现。

#### Acceptance Criteria

1. WHEN 用户提供策略代码和时间范围 THEN THE Game_Loop SHALL 自动执行策略直到结束日期
2. WHEN 自动回测完成 THEN THE Game_Loop SHALL 生成包含所有交易记录的报告
3. THE Game_Loop SHALL 在每个交易日调用用户策略函数并执行返回的交易指令

### Requirement 8: 绩效指标计算

**User Story:** As a 用户, I want to 查看交易绩效指标, so that 我可以评估策略的有效性。

#### Acceptance Criteria

1. WHEN 查询绩效 THEN THE Game_Loop SHALL 计算最终收益率：(期末总资产 - 初始资金) / 初始资金
2. WHEN 查询绩效 THEN THE Game_Loop SHALL 计算最大回撤：净值曲线从最高点回落的最大幅度
3. WHEN 查询绩效 THEN THE Game_Loop SHALL 计算胜率：盈利交易次数 / 总交易次数
4. WHEN 查询绩效 THEN THE Game_Loop SHALL 计算夏普比率：评估单位风险下的超额回报

### Requirement 9: 数据持久化

**User Story:** As a 用户, I want to 保存交易记录和账户状态, so that 我可以在下次继续游戏或分析历史交易。

#### Acceptance Criteria

1. THE Data_Engine SHALL 将下载的行情数据保存为 CSV 或 SQLite 格式
2. THE Account_System SHALL 支持将账户状态序列化保存到文件
3. THE Account_System SHALL 支持从文件反序列化恢复账户状态
4. THE Trading_Engine SHALL 记录所有交易到交易日志
