# Implementation Plan: Achievement System

## Overview

本实现计划将成就系统分为后端服务、前端组件和集成测试三个主要部分。采用增量开发方式，先实现核心数据模型和服务，再构建UI组件，最后进行集成。

## Tasks

- [x] 1. 设置成就系统基础结构
  - [x] 1.1 创建成就系统数据模型和枚举类型
    - 在 `api/services/` 下创建 `achievement_models.py`
    - 定义 AchievementRarity, AchievementCategory, ProgressType, GameMode, ChallengeDifficulty 枚举
    - 定义 AchievementDefinition, AchievementProgress, UnlockedAchievement 数据类
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 1.2 编写成就数据模型的属性测试
    - **Property 1: Achievement Data Round-Trip Consistency**
    - **Property 2: Achievement Definition Completeness**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.6**

- [x] 2. 实现成就定义和基础服务
  - [x] 2.1 创建成就定义配置文件
    - 在 `api/services/` 下创建 `achievement_definitions.py`
    - 定义所有成就（交易类、收益类、里程碑类、连续类、做T类、特殊类、挑战类）
    - 包含成就ID、名称、描述、图标、分类、稀有度、目标值
    - _Requirements: 1.1, 2.1-2.6, 3.1-3.7, 4.1-4.6, 5.1-5.5, 6.1-6.5, 8.1-8.10, 19.1-19.8_
  - [x] 2.2 实现成就服务核心逻辑
    - 在 `api/services/` 下创建 `achievement_service.py`
    - 实现 get_all_definitions, get_achievement_progress, check_and_unlock_achievements
    - 实现各类成就的检查条件函数
    - _Requirements: 1.4, 1.5, 2.1-2.6, 3.1-3.7, 4.1-4.6, 5.1-5.6_
  - [x] 2.3 编写成就阈值的属性测试
    - **Property 3: Trade Count Achievement Thresholds**
    - **Property 4: Profit Achievement Thresholds**
    - **Property 5: Milestone Achievement Thresholds**
    - **Property 6: Streak Detection Correctness**
    - **Property 13: New Save Achievement Initialization**
    - **Validates: Requirements 1.4, 2.1-2.6, 3.1-3.7, 4.1-4.6, 5.1-5.6**

- [x] 3. Checkpoint - 确保成就基础服务测试通过
  - 运行所有属性测试，确保通过
  - 如有问题请询问用户

- [x] 4. 实现做T统计服务
  - [x] 4.1 创建做T数据模型
    - 在 `api/services/` 下创建 `t_trade_models.py`
    - 定义 TTradeRecord, TTradeStatistics 数据类
    - _Requirements: 7.1, 7.2_
  - [x] 4.2 实现做T检测和统计服务
    - 在 `api/services/` 下创建 `t_trade_service.py`
    - 实现 detect_t_trades 从交易历史检测做T
    - 实现 calculate_statistics 计算做T统计数据
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_
  - [x] 4.3 编写做T服务的属性测试
    - **Property 7: T-Trade Detection Accuracy**
    - **Property 8: T-Trade Profit Calculation**
    - **Property 9: T-Trade Achievement Thresholds**
    - **Validates: Requirements 7.1, 7.7, 8.1-8.6**

- [x] 5. 实现挑战模式服务
  - [x] 5.1 创建挑战模式数据模型
    - 在 `api/services/` 下创建 `challenge_models.py`
    - 定义 ChallengeConfig, ChallengeResult, ChallengeProgress 数据类
    - 定义预设挑战配置（简单、中等、困难）
    - _Requirements: 16.1, 17.1, 17.2, 17.6_
  - [x] 5.2 实现挑战模式服务
    - 在 `api/services/` 下创建 `challenge_service.py`
    - 实现 get_available_challenges, create_challenge_save, evaluate_challenge
    - 实现挑战进度计算和结果评估
    - _Requirements: 16.3, 16.4, 17.3, 17.4, 17.5, 18.1-18.6_
  - [x] 5.3 编写挑战模式的属性测试
    - **Property 10: Challenge Mode Constraints**
    - **Property 11: Challenge Evaluation Correctness**
    - **Validates: Requirements 16.4, 17.4, 17.5, 18.1-18.3**

- [x] 6. 实现排行榜服务
  - [x] 6.1 创建排行榜数据模型和服务
    - 在 `api/services/` 下创建 `leaderboard_service.py`
    - 定义 LeaderboardType, LeaderboardEntry 数据类
    - 实现 get_leaderboard 方法，支持多种排名类型
    - _Requirements: 12.1-12.9, 20.1-20.6_
  - [x] 6.2 编写排行榜的属性测试
    - **Property 12: Leaderboard Ordering**
    - **Validates: Requirements 12.1-12.6**

- [x] 7. Checkpoint - 确保所有后端服务测试通过
  - 运行所有属性测试，确保通过
  - 如有问题请询问用户

- [x] 8. 扩展存档系统以支持成就数据
  - [x] 8.1 更新存档数据模型
    - 修改 `api/services/save_service.py` 中的 SaveData 类
    - 添加 game_mode, challenge_config, achievement_progress, t_trade_statistics 字段
    - 更新 to_dict 和 from_dict 方法
    - _Requirements: 1.5, 14.1, 14.2, 14.4, 16.5_
  - [x] 8.2 实现成就数据持久化
    - 在保存/加载存档时包含成就数据
    - 实现成就数据缺失时的重新计算逻辑
    - _Requirements: 14.1, 14.2, 14.3_

- [x] 9. 创建后端API路由
  - [x] 9.1 创建成就API路由
    - 在 `api/routers/` 下创建 `achievements.py`
    - GET /achievements/definitions - 获取所有成就定义
    - GET /achievements/{save_id}/progress - 获取成就进度
    - POST /achievements/{save_id}/check - 检查并解锁成就
    - _Requirements: 7.1-7.5, 10.1-10.5_
  - [x] 9.2 创建做T统计API路由
    - 在 `api/routers/` 下创建 `t_trades.py`
    - GET /t-trades/{save_id}/statistics - 获取做T统计
    - GET /t-trades/{save_id}/history - 获取做T历史
    - _Requirements: 9.1-9.6_
  - [x] 9.3 创建挑战模式API路由
    - 在 `api/routers/` 下创建 `challenges.py`
    - GET /challenges - 获取可用挑战
    - POST /challenges/create - 创建挑战存档
    - GET /challenges/{save_id}/progress - 获取挑战进度
    - POST /challenges/{save_id}/evaluate - 评估挑战结果
    - _Requirements: 16.1-16.6, 17.1-17.6, 18.1-18.6_
  - [x] 9.4 创建排行榜API路由
    - 在 `api/routers/` 下创建 `leaderboard.py`
    - GET /leaderboard/{type} - 获取排行榜
    - _Requirements: 12.1-12.9, 20.1-20.6_
  - [x] 9.5 注册所有新路由到主应用
    - 修改 `api/main.py` 注册新路由
    - _Requirements: 15.1_

- [x] 10. Checkpoint - 确保后端API可用
  - 测试所有API端点
  - 如有问题请询问用户

- [x] 11. 创建前端类型定义
  - [x] 11.1 添加成就系统TypeScript类型
    - 修改 `frontend/src/types/index.ts`
    - 添加 Achievement, AchievementProgress, TTradeRecord, TTradeStatistics 等类型
    - 添加 GameMode, ChallengeDifficulty, ChallengeConfig 等类型
    - _Requirements: 1.1, 7.2, 16.1, 17.1_

- [x] 12. 创建前端API服务
  - [x] 12.1 创建成就API服务
    - 在 `frontend/src/services/` 下创建 `achievementApi.ts`
    - 实现获取成就定义、进度、检查解锁等API调用
    - _Requirements: 10.1-10.5, 15.2_
  - [x] 12.2 创建做T统计API服务
    - 在 `frontend/src/services/` 下创建 `tTradeApi.ts`
    - 实现获取做T统计和历史的API调用
    - _Requirements: 9.1-9.6_
  - [x] 12.3 创建挑战模式API服务
    - 在 `frontend/src/services/` 下创建 `challengeApi.ts`
    - 实现挑战相关API调用
    - _Requirements: 16.1-16.6, 17.1-17.6, 18.1-18.6_
  - [x] 12.4 创建排行榜API服务
    - 在 `frontend/src/services/` 下创建 `leaderboardApi.ts`
    - 实现排行榜API调用
    - _Requirements: 12.1-12.9, 20.1-20.6_

- [x] 13. 实现成就UI组件
  - [x] 13.1 创建成就卡片组件
    - 在 `frontend/src/components/` 下创建 `AchievementCard.tsx`
    - 显示成就图标、名称、描述、稀有度、进度条
    - 区分已解锁/进行中/未解锁状态
    - 支持亮色/暗色主题
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 15.5_
  - [x] 13.2 创建成就通知组件
    - 在 `frontend/src/components/` 下创建 `AchievementNotification.tsx`
    - 实现解锁成就时的弹出通知
    - 根据稀有度显示不同动画效果
    - 5秒后自动消失或点击关闭
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  - [x] 13.3 创建成就弹窗组件
    - 在 `frontend/src/components/` 下创建 `AchievementModal.tsx`
    - 显示所有成就列表，支持分类筛选
    - 显示成就统计（完成数/总数、各分类完成率）
    - 支持按分类、稀有度、状态排序
    - _Requirements: 10.5, 13.1-13.6, 15.2, 15.4_

- [x] 14. 实现做T统计UI组件
  - [x] 14.1 创建做T统计面板组件
    - 在 `frontend/src/components/` 下创建 `TTradeStatsPanel.tsx`
    - 显示做T总数、成功数、成功率
    - 显示累计盈亏、最佳/最差单次做T
    - 显示做T历史列表
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  - [ ] 14.2 创建做T趋势图组件
    - 在 `frontend/src/components/` 下创建 `TTradeChart.tsx`
    - 显示做T收益趋势图
    - 支持按日期筛选
    - _Requirements: 9.5, 9.6_

- [x] 15. 实现挑战模式UI组件
  - [x] 15.1 创建挑战选择组件
    - 在 `frontend/src/components/` 下创建 `ChallengeSelector.tsx`
    - 显示可用挑战列表
    - 显示挑战难度、目标、时间范围
    - _Requirements: 16.1, 16.2, 17.1, 17.2_
  - [x] 15.2 创建挑战进度组件
    - 在 `frontend/src/components/` 下创建 `ChallengeProgress.tsx`
    - 显示当前资产、目标资产、进度百分比
    - 显示剩余时间
    - _Requirements: 17.3_
  - [x] 15.3 创建挑战结果组件
    - 在 `frontend/src/components/` 下创建 `ChallengeResult.tsx`
    - 显示挑战成功/失败结果
    - 成功时显示庆祝动画
    - _Requirements: 18.2, 18.3, 18.4_

- [x] 16. 实现排行榜UI组件
  - [x] 16.1 创建排行榜面板组件
    - 在 `frontend/src/components/` 下创建 `LeaderboardPanel.tsx`
    - 显示排名列表（排名、存档名、指标值、成就数）
    - 支持切换排名类型
    - 高亮当前存档
    - _Requirements: 12.7, 12.8, 12.9, 20.1-20.6_

- [x] 17. 集成成就系统到主界面
  - [x] 17.1 更新主页支持游戏模式选择
    - 修改 `frontend/src/pages/HomePage.tsx`
    - 在创建存档弹窗中添加模式选择（自由/挑战）
    - 挑战模式显示挑战选择器
    - 存档列表显示游戏模式标签
    - _Requirements: 16.1, 16.2, 16.5, 16.6_
  - [x] 17.2 更新交易界面集成成就按钮
    - 修改 `frontend/src/pages/TradingView.tsx`
    - 在头部添加成就按钮（带新成就数量徽章）
    - 点击打开成就弹窗
    - 挑战模式显示挑战进度
    - _Requirements: 15.1, 15.2, 15.3, 17.3_
  - [x] 17.3 实现成就解锁检测和通知
    - 在交易完成、日结束等时机检查成就
    - 解锁新成就时显示通知
    - _Requirements: 11.1-11.5_

- [x] 18. Checkpoint - 确保前端组件正常工作
  - 测试所有UI组件
  - 测试成就解锁流程
  - 如有问题请询问用户

- [x] 19. 编写集成测试
  - [x] 19.1 编写成就系统集成测试
    - 在 `tests/integration/` 下创建 `test_achievement_flow.py`
    - 测试完整的成就解锁流程
    - 测试成就数据持久化
    - _Requirements: 14.1-14.5_
  - [x] 19.2 编写挑战模式集成测试
    - 在 `tests/integration/` 下创建 `test_challenge_flow.py`
    - 测试挑战创建、进行、完成流程
    - _Requirements: 16.1-16.6, 17.1-17.6, 18.1-18.6_

- [x] 20. Final Checkpoint - 确保所有测试通过
  - 运行所有单元测试和属性测试
  - 运行所有集成测试
  - 如有问题请询问用户

## Notes

- All tasks are required for complete implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- 后端使用 Python + FastAPI，前端使用 React + TypeScript + Ant Design
- 属性测试使用 Hypothesis 库
