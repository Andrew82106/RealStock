# Implementation Plan: A 股模拟交易回测系统

## Overview

本实现计划将系统分为 6 个主要阶段：项目初始化、数据层、账户系统、交易引擎、播放引擎和模拟器集成。每个阶段包含核心实现和属性测试任务。

## Tasks

- [x] 1. 项目初始化和基础设施
  - [x] 1.1 创建项目目录结构和配置文件
    - 创建 `src/` 目录结构：`data_engine/`, `account/`, `trading/`, `playback/`, `simulator/`
    - 创建 `tests/` 目录结构：`unit/`, `property/`, `integration/`
    - 创建 `pyproject.toml` 配置 Python 项目
    - 添加依赖：akshare, pandas, numpy, pytest, hypothesis
    - _Requirements: 项目基础设施_

  - [x] 1.2 创建自定义异常类
    - 在 `src/exceptions.py` 中定义所有异常类
    - `TradingSimulatorError`, `DataFetchError`, `InvalidStockCodeError`, `InvalidDateRangeError`, `InvalidOrderError`
    - _Requirements: 错误处理_

- [x] 2. 数据引擎模块 (DataEngine)
  - [x] 2.1 实现 StockInfo 数据类和 DataEngine 基础结构
    - 创建 `src/data_engine/models.py` 定义 StockInfo
    - 创建 `src/data_engine/engine.py` 定义 DataEngine 类框架
    - 实现 `normalize_code()` 方法处理股票代码格式
    - _Requirements: 1.1_

  - [x] 2.2 实现股票列表获取功能
    - 实现 `get_stock_list()` 调用 AkShare API
    - 处理 API 异常并转换为自定义异常
    - _Requirements: 1.1_

  - [x] 2.3 实现日线数据获取和缓存
    - 实现 `get_daily_data()` 方法
    - 实现 `_load_from_cache()` 和 `_save_to_cache()` 方法
    - 支持前复权数据（adjust="qfq"）
    - _Requirements: 1.2, 1.3, 1.4, 1.5_

  - [x] 2.4 编写属性测试：日线数据完整性
    - **Property 1.2: 日线数据字段完整性**
    - 验证返回的 DataFrame 包含所有必需字段
    - **Validates: Requirements 1.2**

  - [x] 2.5 实现分时数据获取和模拟生成
    - 实现 `get_intraday_data()` 方法
    - 实现 `generate_simulated_intraday()` 基于日线数据模拟分时走势
    - 生成 240 个数据点（9:30-11:30, 13:00-15:00）
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 2.6 编写属性测试：模拟分时数据一致性
    - **Property 18: 模拟分时数据一致性**
    - 验证分时数据与日线数据的价格范围一致
    - **Validates: Requirements 10.4**

- [x] 3. Checkpoint - 数据层完成
  - 确保所有测试通过，如有问题请询问用户

- [x] 4. 账户系统模块 (Account)
  - [x] 4.1 实现 Position 和 TradeFee 数据类
    - 创建 `src/account/models.py`
    - 实现 Position 类及其属性（market_value, profit_loss, profit_loss_pct）
    - 实现 TradeFee 配置类
    - _Requirements: 2.3_

  - [x] 4.2 编写属性测试：持仓浮动盈亏计算
    - **Property 17: 持仓浮动盈亏计算**
    - 验证 profit_loss 和 profit_loss_pct 计算正确
    - **Validates: Requirements 2.3**

  - [x] 4.3 实现 Account 类核心功能
    - 创建 `src/account/account.py`
    - 实现初始化、total_market_value、total_assets 属性
    - 实现 calculate_buy_fee() 和 calculate_sell_fee() 方法
    - 实现 update_prices() 方法
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_

  - [x] 4.4 编写属性测试：账户总资产不变量
    - **Property 1: 账户总资产不变量**
    - 验证 total_assets == cash + total_market_value
    - **Validates: Requirements 2.4**

  - [x] 4.5 编写属性测试：交易费用计算
    - **Property 2: 交易费用计算正确性**
    - 验证买入佣金和卖出费用计算正确
    - **Validates: Requirements 2.5, 2.6**

  - [x] 4.6 实现账户序列化和反序列化
    - 实现 to_dict() 和 from_dict() 方法
    - 实现 save() 和 load() 方法
    - _Requirements: 9.2, 9.3_

  - [x] 4.7 编写属性测试：账户序列化 Round-Trip
    - **Property 16: 账户序列化 Round-Trip**
    - 验证序列化后反序列化得到等价账户
    - **Validates: Requirements 9.2, 9.3**

- [x] 5. Checkpoint - 账户系统完成
  - 确保所有测试通过，如有问题请询问用户

- [x] 6. 交易引擎模块 (TradingEngine)
  - [x] 6.1 实现订单相关数据类
    - 创建 `src/trading/models.py`
    - 实现 OrderType, OrderStatus 枚举
    - 实现 Order 和 DailyBar 数据类
    - _Requirements: 交易基础设施_

  - [x] 6.2 实现 TradingEngine 买入逻辑
    - 创建 `src/trading/engine.py`
    - 实现 submit_buy_order() 方法
    - 实现资金验证和价格范围验证
    - 实现 _execute_buy() 更新账户
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 6.3 编写属性测试：买入订单验证
    - **Property 3: 买入订单资金验证**
    - 验证资金充足时接受订单，不足时拒绝
    - **Validates: Requirements 3.1, 3.2**

  - [x] 6.4 编写属性测试：买入后账户状态
    - **Property 4: 买入后账户状态一致性**
    - 验证买入后现金和持仓变化正确
    - **Validates: Requirements 3.3**

  - [x] 6.5 实现 TradingEngine 卖出逻辑
    - 实现 submit_sell_order() 方法
    - 实现持仓验证、T+1 验证和价格范围验证
    - 实现 _execute_sell() 更新账户
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3_

  - [x] 6.6 编写属性测试：卖出订单验证
    - **Property 5: 卖出订单持仓验证**
    - 验证持仓充足时接受订单，不足时拒绝
    - **Validates: Requirements 4.1, 4.2**

  - [x] 6.7 编写属性测试：卖出后账户状态
    - **Property 6: 卖出后账户状态一致性**
    - 验证卖出后现金和持仓变化正确
    - **Validates: Requirements 4.3**

  - [x] 6.8 编写属性测试：价格范围验证
    - **Property 7: 回测模式价格范围验证**
    - 验证委托价格在日线范围内时有效
    - **Validates: Requirements 3.4, 4.4**

  - [x] 6.9 编写属性测试：T+1 限制
    - **Property 8: T+1 交易限制**
    - 验证当天买入不可卖出，次日可卖
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [x] 6.10 实现交易日志记录
    - 实现 get_trade_history() 方法
    - 支持导出交易日志到 CSV
    - _Requirements: 9.4_

- [x] 7. Checkpoint - 交易引擎完成
  - 确保所有测试通过，如有问题请询问用户

- [x] 8. 播放引擎模块 (PlaybackEngine)
  - [x] 8.1 实现播放状态和配置数据类
    - 创建 `src/playback/models.py`
    - 实现 PlaybackState 枚举
    - 实现 IntradayTick 和 PlaybackConfig 数据类
    - _Requirements: 6.1_

  - [x] 8.2 实现 PlaybackEngine 核心功能
    - 创建 `src/playback/engine.py`
    - 实现 setup(), load_day(), set_speed() 方法
    - 实现 play(), pause(), tick() 方法
    - 实现 get_current_prices(), next_day() 方法
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [x] 8.3 编写属性测试：播放状态转换
    - **Property 9: 日内播放状态转换**
    - 验证状态机转换正确
    - **Validates: Requirements 6.1, 6.3, 6.4, 6.5, 6.6, 6.8**

  - [x] 8.4 实现播放循环和回调机制
    - 实现 on_tick(), on_day_end() 回调注册
    - 实现 run_playback_loop() 阻塞式播放
    - _Requirements: 6.2, 6.7_

  - [x] 8.5 编写属性测试：日内价格更新
    - **Property 10: 日内价格更新一致性**
    - 验证 tick 时持仓价格正确更新
    - **Validates: Requirements 6.7**

- [x] 9. Checkpoint - 播放引擎完成
  - 确保所有测试通过，如有问题请询问用户

- [x] 10. 模拟器集成 (Simulator)
  - [x] 10.1 实现 Simulator 基础结构
    - 创建 `src/simulator/simulator.py`
    - 实现 setup() 初始化所有组件
    - 实现 get_current_bars() 方法
    - _Requirements: 模拟器基础_

  - [x] 10.2 实现日内播放模式集成
    - 实现 start_day(), play(), pause() 方法
    - 实现 buy(), sell() 方法（仅暂停状态可用）
    - 实现 next_day() 方法
    - _Requirements: 6.1, 6.3, 6.5, 6.6_

  - [x] 10.3 编写属性测试：交易状态限制
    - **Property 11: 交易仅在暂停状态可用**
    - 验证非暂停状态下交易抛出错误
    - **Validates: Requirements 6.3**

  - [x] 10.4 实现自动回测模式
    - 实现 run_backtest() 方法
    - 实现策略函数调用和交易执行
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 10.5 编写属性测试：回测遍历完整性
    - **Property 12: 回测遍历完整性**
    - 验证策略函数在每个交易日被调用
    - **Validates: Requirements 7.1, 7.3**

  - [x] 10.6 实现绩效指标计算
    - 实现 calculate_metrics() 方法
    - 实现 _calculate_max_drawdown(), _calculate_sharpe_ratio(), _calculate_win_rate()
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 10.7 编写属性测试：收益率计算
    - **Property 13: 收益率计算正确性**
    - 验证 total_return 计算公式正确
    - **Validates: Requirements 8.1**

  - [x] 10.8 编写属性测试：最大回撤计算
    - **Property 14: 最大回撤计算正确性**
    - 验证 max_drawdown 计算正确
    - **Validates: Requirements 8.2**

  - [x] 10.9 编写属性测试：胜率计算
    - **Property 15: 胜率计算正确性**
    - 验证 win_rate 计算正确
    - **Validates: Requirements 8.3**

- [x] 11. Checkpoint - 模拟器完成
  - 确保所有测试通过，如有问题请询问用户

- [x] 12. 集成测试和示例
  - [x] 12.1 编写集成测试
    - 测试完整的买入-持有-卖出流程
    - 测试多只股票的回测流程
    - 测试日内播放模式的完整流程
    - _Requirements: 集成验证_

  - [x] 12.2 创建使用示例
    - 创建 `examples/simple_backtest.py` 简单回测示例
    - 创建 `examples/interactive_play.py` 交互式播放示例
    - 添加 README 使用说明
    - _Requirements: 用户文档_

- [x] 13. Final Checkpoint - 项目完成
  - 确保所有测试通过，如有问题请询问用户

## Notes

- 所有任务均为必需，包括属性测试
- 每个 Checkpoint 用于验证阶段性成果
- 属性测试使用 hypothesis 库，每个测试运行 100 次迭代
- 建议先用 3-5 只股票进行测试，避免大量 API 调用
