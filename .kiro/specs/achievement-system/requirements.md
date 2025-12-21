# Requirements Document

## Introduction

成就系统是A股模拟交易系统的游戏化功能模块，旨在通过设计有吸引力的成就目标、排行榜和可视化效果，激励用户持续参与模拟交易，提升用户体验和留存率。系统将追踪用户的交易行为、账户表现和里程碑事件，解锁相应成就并提供视觉反馈。

## Glossary

- **Achievement_System**: 成就系统，负责追踪用户行为、计算成就进度、解锁成就和展示成就信息的核心模块
- **Achievement**: 成就，用户通过完成特定条件获得的奖励标识，包含名称、描述、图标、稀有度等属性
- **Achievement_Category**: 成就分类，将成就按主题分组（如交易类、收益类、里程碑类等）
- **Achievement_Progress**: 成就进度，追踪用户完成成就条件的当前状态
- **Leaderboard**: 排行榜，按特定指标对所有存档进行排名展示
- **Achievement_Notification**: 成就通知，用户解锁成就时的视觉和音效反馈
- **Rarity**: 稀有度，成就的稀有程度分级（普通、稀有、史诗、传说）
- **Save_Data**: 存档数据，包含用户账户、交易历史、资产历史等信息
- **T_Trade**: 做T交易，指在T+1规则下，利用已有持仓在同一交易日内先卖后买（正T）或先买后卖（反T，需次日卖出）的操作策略
- **T_Trade_Statistics**: 做T统计，追踪用户做T操作的次数、成功率、收益等数据
- **Successful_T_Trade**: 成功的做T，指通过做T操作获得正收益的交易
- **Free_Mode**: 自由模式，用户可自由设定开始/结束日期、初始资金和股票池的游戏模式
- **Challenge_Mode**: 挑战模式，系统预设固定条件（初始资金1万、单只股票、固定时间段），需在规定时间内达到目标资金的竞技模式
- **Challenge_Target**: 挑战目标，挑战模式中需要达到的目标资金金额
- **Challenge_Result**: 挑战结果，挑战模式结束时的成功/失败状态

## Requirements

### Requirement 1: Achievement Definition and Storage

**User Story:** As a player, I want the system to define and store various achievements, so that I have clear goals to pursue during trading.

#### Acceptance Criteria

1. THE Achievement_System SHALL define achievements with the following attributes: id, name, description, icon, category, rarity, unlock_condition, and progress_type
2. THE Achievement_System SHALL support four rarity levels: common (普通), rare (稀有), epic (史诗), and legendary (传说)
3. THE Achievement_System SHALL categorize achievements into at least six categories: trading (交易), profit (收益), milestone (里程碑), streak (连续), t_trade (做T), and special (特殊)
4. WHEN a new save is created, THE Achievement_System SHALL initialize an empty achievement progress record for that save
5. THE Achievement_System SHALL persist achievement progress data alongside save data using JSON serialization
6. FOR ALL achievement data, serializing then deserializing SHALL produce an equivalent achievement record (round-trip property)

### Requirement 2: Trading Achievement Tracking

**User Story:** As a player, I want to earn achievements for my trading activities, so that I feel rewarded for active participation.

#### Acceptance Criteria

1. WHEN a user completes their first buy order, THE Achievement_System SHALL unlock the "First Trade" achievement
2. WHEN a user completes 10 total trades, THE Achievement_System SHALL unlock the "Active Trader" achievement
3. WHEN a user completes 100 total trades, THE Achievement_System SHALL unlock the "Trading Master" achievement
4. WHEN a user holds 5 different stocks simultaneously, THE Achievement_System SHALL unlock the "Diversified Portfolio" achievement
5. WHEN a user executes a single trade worth over 100,000 yuan, THE Achievement_System SHALL unlock the "Big Spender" achievement
6. THE Achievement_System SHALL track cumulative trade count across all trading sessions within a save

### Requirement 3: Profit Achievement Tracking

**User Story:** As a player, I want to earn achievements for profitable trading, so that I am motivated to improve my trading skills.

#### Acceptance Criteria

1. WHEN a user's total return exceeds 10%, THE Achievement_System SHALL unlock the "Profitable Beginner" achievement
2. WHEN a user's total return exceeds 50%, THE Achievement_System SHALL unlock the "Skilled Investor" achievement
3. WHEN a user's total return exceeds 100%, THE Achievement_System SHALL unlock the "Double Your Money" achievement
4. WHEN a user's total return exceeds 500%, THE Achievement_System SHALL unlock the "Trading Legend" achievement
5. WHEN a user earns 10,000 yuan profit in a single day, THE Achievement_System SHALL unlock the "Daily Winner" achievement
6. WHEN a user earns 100,000 yuan profit in a single day, THE Achievement_System SHALL unlock the "Jackpot Day" achievement
7. THE Achievement_System SHALL calculate profit based on the difference between current total assets and initial cash

### Requirement 4: Milestone Achievement Tracking

**User Story:** As a player, I want to earn achievements for reaching account milestones, so that I can track my long-term progress.

#### Acceptance Criteria

1. WHEN a user's total assets reach 200,000 yuan (starting from 100,000), THE Achievement_System SHALL unlock the "First Milestone" achievement
2. WHEN a user's total assets reach 500,000 yuan, THE Achievement_System SHALL unlock the "Half Millionaire" achievement
3. WHEN a user's total assets reach 1,000,000 yuan, THE Achievement_System SHALL unlock the "Millionaire" achievement
4. WHEN a user completes 30 trading days, THE Achievement_System SHALL unlock the "Monthly Trader" achievement
5. WHEN a user completes 250 trading days (approximately one year), THE Achievement_System SHALL unlock the "Annual Veteran" achievement
6. THE Achievement_System SHALL track trading days based on the count of daily snapshots in asset history

### Requirement 5: Streak Achievement Tracking

**User Story:** As a player, I want to earn achievements for consistent performance, so that I am encouraged to maintain good trading habits.

#### Acceptance Criteria

1. WHEN a user achieves 3 consecutive profitable days, THE Achievement_System SHALL unlock the "Winning Streak" achievement
2. WHEN a user achieves 7 consecutive profitable days, THE Achievement_System SHALL unlock the "Hot Hand" achievement
3. WHEN a user achieves 30 consecutive profitable days, THE Achievement_System SHALL unlock the "Unstoppable" achievement
4. WHEN a user trades on 5 consecutive trading days, THE Achievement_System SHALL unlock the "Dedicated Trader" achievement
5. THE Achievement_System SHALL calculate consecutive profitable days based on daily_return values in asset history
6. IF a user's streak is broken, THEN THE Achievement_System SHALL reset the streak counter to zero

### Requirement 6: Special Achievement Tracking

**User Story:** As a player, I want to earn special achievements for unique accomplishments, so that I have rare goals to pursue.

#### Acceptance Criteria

1. WHEN a user catches a stock at its daily limit up (涨停), THE Achievement_System SHALL unlock the "Limit Hunter" achievement
2. WHEN a user successfully avoids a stock's daily limit down (跌停) by selling before it happens, THE Achievement_System SHALL unlock the "Risk Avoider" achievement
3. WHEN a user's single stock position gains over 50%, THE Achievement_System SHALL unlock the "Stock Picker" achievement
4. WHEN a user recovers from a 20% drawdown to break even, THE Achievement_System SHALL unlock the "Comeback King" achievement
5. WHEN a user maintains a Sharpe ratio above 2.0 for 30 days, THE Achievement_System SHALL unlock the "Risk Master" achievement

### Requirement 7: T-Trade Statistics Tracking

**User Story:** As a player, I want the system to track my T-trade (做T) activities, so that I can analyze and improve my intraday trading skills.

#### Acceptance Criteria

1. THE T_Trade_Statistics SHALL detect a T-trade when a user sells existing shares and buys back the same stock on the same trading day
2. THE T_Trade_Statistics SHALL record each T-trade with: stock code, sell price, buy price, quantity, profit/loss, and trade date
3. THE T_Trade_Statistics SHALL calculate T-trade success rate as (profitable T-trades / total T-trades)
4. THE T_Trade_Statistics SHALL calculate total T-trade profit/loss across all T-trades
5. THE T_Trade_Statistics SHALL track the best single T-trade profit and worst single T-trade loss
6. THE T_Trade_Statistics SHALL persist T-trade statistics alongside save data
7. FOR ALL T-trade records, the profit calculation SHALL equal (sell_price - buy_price) * quantity - fees

### Requirement 8: T-Trade Achievement Tracking

**User Story:** As a player, I want to earn achievements for successful T-trading, so that I am motivated to master this advanced trading technique.

#### Acceptance Criteria

1. WHEN a user completes their first T-trade, THE Achievement_System SHALL unlock the "T-Trade Beginner" achievement
2. WHEN a user completes 10 successful T-trades, THE Achievement_System SHALL unlock the "T-Trade Apprentice" achievement
3. WHEN a user completes 50 successful T-trades, THE Achievement_System SHALL unlock the "T-Trade Expert" achievement
4. WHEN a user completes 100 successful T-trades, THE Achievement_System SHALL unlock the "T-Trade Master" achievement
5. WHEN a user achieves a T-trade success rate above 60% with at least 20 T-trades, THE Achievement_System SHALL unlock the "Consistent T-Trader" achievement
6. WHEN a user achieves a T-trade success rate above 80% with at least 50 T-trades, THE Achievement_System SHALL unlock the "T-Trade Perfectionist" achievement
7. WHEN a user earns over 1,000 yuan profit from a single T-trade, THE Achievement_System SHALL unlock the "Big T Win" achievement
8. WHEN a user earns over 10,000 yuan profit from a single T-trade, THE Achievement_System SHALL unlock the "T-Trade Jackpot" achievement
9. WHEN a user's cumulative T-trade profit exceeds 50,000 yuan, THE Achievement_System SHALL unlock the "T-Trade Millionaire" achievement
10. WHEN a user completes 5 successful T-trades in a single day, THE Achievement_System SHALL unlock the "Day Trader" achievement

### Requirement 9: T-Trade Statistics Display

**User Story:** As a player, I want to see my T-trade statistics in a dedicated panel, so that I can track my T-trading performance.

#### Acceptance Criteria

1. THE Achievement_System SHALL display a T-trade statistics panel showing total T-trades, successful T-trades, and success rate
2. THE Achievement_System SHALL display cumulative T-trade profit/loss with visual indication (green for profit, red for loss)
3. THE Achievement_System SHALL display best and worst single T-trade results
4. THE Achievement_System SHALL display a T-trade history list with date, stock, prices, and profit/loss
5. THE Achievement_System SHALL display T-trade performance trend chart showing profit over time
6. THE Achievement_System SHALL allow filtering T-trade history by stock code and date range

### Requirement 10: Achievement Progress Display

**User Story:** As a player, I want to see my achievement progress, so that I know how close I am to unlocking achievements.

#### Acceptance Criteria

1. THE Achievement_System SHALL display a progress bar for achievements that have measurable progress
2. WHEN displaying achievement progress, THE Achievement_System SHALL show current value and target value (e.g., "5/10 trades")
3. THE Achievement_System SHALL visually distinguish between locked, in-progress, and unlocked achievements
4. THE Achievement_System SHALL display achievement unlock date for completed achievements
5. THE Achievement_System SHALL sort achievements by category, then by rarity, then by unlock status

### Requirement 11: Achievement Notification System

**User Story:** As a player, I want to receive visual feedback when I unlock an achievement, so that I feel a sense of accomplishment.

#### Acceptance Criteria

1. WHEN an achievement is unlocked, THE Achievement_System SHALL display a notification popup with the achievement name, icon, and rarity
2. THE Achievement_Notification SHALL include an animation effect appropriate to the achievement rarity
3. THE Achievement_Notification SHALL auto-dismiss after 5 seconds or when the user clicks to dismiss
4. WHEN multiple achievements are unlocked simultaneously, THE Achievement_System SHALL queue notifications and display them sequentially
5. THE Achievement_System SHALL play a sound effect when an achievement is unlocked (with user preference to disable)

### Requirement 12: Leaderboard System

**User Story:** As a player, I want to see how my performance compares to my other saves, so that I can compete with myself and track improvement.

#### Acceptance Criteria

1. THE Leaderboard SHALL rank saves by total return percentage
2. THE Leaderboard SHALL rank saves by total assets
3. THE Leaderboard SHALL rank saves by number of achievements unlocked
4. THE Leaderboard SHALL rank saves by Sharpe ratio
5. THE Leaderboard SHALL rank saves by T-trade success rate (minimum 10 T-trades required)
6. THE Leaderboard SHALL rank saves by cumulative T-trade profit
7. WHEN displaying leaderboard, THE Leaderboard SHALL show rank, save name, metric value, and achievement count
8. THE Leaderboard SHALL update rankings whenever a save's metrics change
9. THE Leaderboard SHALL highlight the currently active save in the ranking

### Requirement 13: Achievement Statistics Dashboard

**User Story:** As a player, I want to see an overview of my achievement progress, so that I can understand my overall accomplishment level.

#### Acceptance Criteria

1. THE Achievement_System SHALL display total achievements unlocked out of total available
2. THE Achievement_System SHALL display achievement completion percentage by category
3. THE Achievement_System SHALL display achievement completion percentage by rarity
4. THE Achievement_System SHALL display the most recent achievements unlocked
5. THE Achievement_System SHALL display the rarest achievements unlocked
6. THE Achievement_System SHALL provide a visual representation of achievement progress (e.g., progress ring or bar chart)

### Requirement 14: Achievement Data Persistence

**User Story:** As a player, I want my achievement progress to be saved, so that I don't lose my accomplishments.

#### Acceptance Criteria

1. WHEN a save is updated, THE Achievement_System SHALL persist achievement progress to the save file
2. WHEN a save is loaded, THE Achievement_System SHALL restore achievement progress from the save file
3. IF achievement data is missing or corrupted, THEN THE Achievement_System SHALL recalculate achievements from trade and asset history
4. THE Achievement_System SHALL maintain backward compatibility when new achievements are added
5. FOR ALL valid achievement states, saving then loading SHALL produce an equivalent state (round-trip property)

### Requirement 15: Achievement UI Integration

**User Story:** As a player, I want to access achievements from the main interface, so that I can easily view my progress.

#### Acceptance Criteria

1. THE Achievement_System SHALL provide an achievement button/icon in the trading view header
2. WHEN the achievement button is clicked, THE Achievement_System SHALL open an achievement modal or panel
3. THE Achievement_System SHALL display a badge on the achievement button showing the count of newly unlocked achievements
4. THE Achievement_System SHALL provide category tabs or filters in the achievement view
5. THE Achievement_System SHALL support both light and dark theme for achievement displays

### Requirement 16: Game Mode Selection

**User Story:** As a player, I want to choose between free mode and challenge mode when creating a save, so that I can either practice freely or test my skills under pressure.

#### Acceptance Criteria

1. WHEN creating a new save, THE System SHALL present two mode options: Free Mode and Challenge Mode
2. THE System SHALL clearly display the differences between the two modes before selection
3. WHEN Free Mode is selected, THE System SHALL allow custom initial cash (100 - 100,000,000 yuan), custom date range, and multiple stock selection
4. WHEN Challenge Mode is selected, THE System SHALL set initial cash to 10,000 yuan and restrict to single stock selection
5. THE System SHALL store the game mode in the save data and display it in the save list
6. THE System SHALL visually distinguish Challenge Mode saves from Free Mode saves in the UI

### Requirement 17: Challenge Mode Configuration

**User Story:** As a player, I want to participate in predefined challenges with specific goals, so that I can test my trading skills under competitive conditions.

#### Acceptance Criteria

1. THE Challenge_Mode SHALL provide predefined challenge configurations with fixed start date, end date, and target stock
2. THE Challenge_Mode SHALL set the target asset amount based on challenge difficulty (e.g., 15,000 yuan for easy, 20,000 yuan for medium, 30,000 yuan for hard)
3. THE Challenge_Mode SHALL display the challenge goal, time remaining, and current progress during gameplay
4. THE Challenge_Mode SHALL prevent users from adding additional stocks during the challenge
5. THE Challenge_Mode SHALL prevent users from modifying the initial cash or date range
6. THE System SHALL provide at least 3 different challenge difficulties: Easy (50% return target), Medium (100% return target), Hard (200% return target)

### Requirement 18: Challenge Mode Completion

**User Story:** As a player, I want to know whether I passed or failed a challenge, so that I can track my competitive performance.

#### Acceptance Criteria

1. WHEN the challenge end date is reached, THE System SHALL evaluate whether the target asset amount was achieved
2. IF the target is achieved, THEN THE System SHALL mark the challenge as "Passed" and display a success celebration
3. IF the target is not achieved, THEN THE System SHALL mark the challenge as "Failed" and display the final result
4. THE System SHALL record challenge results (passed/failed, final assets, target assets) in the save data
5. THE System SHALL prevent further trading after the challenge end date is reached
6. THE System SHALL allow users to view their challenge history and statistics

### Requirement 19: Challenge Mode Achievements

**User Story:** As a player, I want to earn special achievements for completing challenges, so that I am motivated to take on difficult challenges.

#### Acceptance Criteria

1. WHEN a user passes their first challenge, THE Achievement_System SHALL unlock the "Challenge Accepted" achievement
2. WHEN a user passes an Easy difficulty challenge, THE Achievement_System SHALL unlock the "Easy Winner" achievement
3. WHEN a user passes a Medium difficulty challenge, THE Achievement_System SHALL unlock the "Medium Master" achievement
4. WHEN a user passes a Hard difficulty challenge, THE Achievement_System SHALL unlock the "Hard Mode Hero" achievement
5. WHEN a user passes 5 challenges of any difficulty, THE Achievement_System SHALL unlock the "Challenge Veteran" achievement
6. WHEN a user passes 3 Hard difficulty challenges, THE Achievement_System SHALL unlock the "Challenge Legend" achievement
7. WHEN a user exceeds the target by 50% in any challenge, THE Achievement_System SHALL unlock the "Overachiever" achievement
8. WHEN a user passes a challenge with only T-trades (no overnight positions), THE Achievement_System SHALL unlock the "Pure T-Trader" achievement

### Requirement 20: Challenge Mode Leaderboard

**User Story:** As a player, I want to see how my challenge performance compares to others, so that I can compete for the best results.

#### Acceptance Criteria

1. THE Leaderboard SHALL have a dedicated Challenge Mode section
2. THE Leaderboard SHALL rank challenge completions by final return percentage for each difficulty level
3. THE Leaderboard SHALL display challenge completion time, final assets, and return percentage
4. THE Leaderboard SHALL show the number of challenges passed vs attempted for each save
5. THE Leaderboard SHALL highlight personal best performances
6. THE Leaderboard SHALL filter by challenge difficulty (Easy/Medium/Hard)
