/**
 * A股模拟交易系统 - 类型定义
 */

// 股票信息
export interface StockInfo {
  code: string;
  name: string;
  market: string;
}

// 日线数据
export interface DailyBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// 持仓
export interface Position {
  code: string;
  quantity: number;
  costPrice: number;
  currentPrice: number;
  profitLoss: number;
  profitLossPct: number;
  buyDate?: string;  // 买入日期，用于T+1判断
}

// 账户
export interface Account {
  cash: number;
  totalAssets: number;
  totalMarketValue: number;
  positions: Position[];
}

// 游戏状态
export interface GameState {
  sessionId: string;
  currentDate: string;
  playbackState: 'idle' | 'playing' | 'paused' | 'day_ended' | 'finished';
  isLastDay: boolean;
}

// 绩效指标
export interface PerformanceMetrics {
  totalReturn: number;
  maxDrawdown: number;
  winRate: number;
  sharpeRatio: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
}

// 交易记录
export interface TradeRecord {
  date: string;
  code: string;
  type: 'buy' | 'sell';
  price: number;
  quantity: number;
  fee: number;
  status: 'filled' | 'rejected';
}

// 挂单记录
export interface PendingOrder {
  orderId: string;
  code: string;
  orderType: 'buy' | 'sell';
  price: number;
  quantity: number;
  frozenCash: number;
  frozenQuantity: number;
}

// API 请求/响应类型
export interface GameStartRequest {
  stock_codes: string[];
  start_date: string;
  end_date: string;
  initial_cash: number;
}

export interface GameStartResponse {
  session_id: string;
  current_date: string;
  trading_dates: string[];
}

export interface OrderRequest {
  session_id: string;
  code: string;
  price: number;
  quantity: number;
}

export interface OrderResponse {
  success: boolean;
  order_id?: string;
  message: string;
  fee?: number;
}

// WebSocket 消息类型
export interface WSMessage {
  type: 'tick' | 'day_end' | 'account_update' | 'state_update' | 'state_change' | 'error';
  data: Record<string, unknown>;
}

export interface TickData {
  tick_index: number;
  prices: Record<string, number>;
  current_date?: string;  // 当前日期，用于实时更新挑战进度
}

export interface AccountUpdateData {
  cash: number;
  total_assets: number;
  total_market_value: number;
  positions: Array<{
    code: string;
    quantity: number;
    cost_price: number;
    current_price: number;
    profit_loss: number;
    profit_loss_pct: number;
  }>;
}

export interface StateUpdateData {
  current_date: string;
  playback_state: string;
  tick_index: number;
  is_last_day: boolean;
}


// 每日资产快照
export interface DailySnapshot {
  date: string;
  totalAssets: number;
  cash: number;
  marketValue: number;
  dailyReturn: number;
  dailyProfit: number;
  cumulativeReturn: number;
}

// 资产历史
export interface AssetHistory {
  initialCash: number;
  currentAssets: number;
  totalReturn: number;
  history: DailySnapshot[];
}

// ============ 存档系统类型 ============

// 存档元数据
export interface SaveMetadata {
  id: string;           // 存档ID (sanitized name)
  name: string;         // 存档显示名称
  createdAt: string;    // 创建时间 ISO 8601
  updatedAt: string;    // 最后更新时间 ISO 8601
  currentDate: string;  // 当前模拟日期
  totalAssets: number;  // 总资产
  stockCount: number;   // 股票数量
}

// 存档配置
export interface SaveConfig {
  initialCash: number;
  startDate: string;
  endDate: string;
}

// 存档账户状态
export interface SaveAccountState {
  cash: number;
  positions: Position[];
}

// 存档游戏状态
export interface SaveGameState {
  currentDate: string;
  playbackState: string;
  tickIndex: number;
  sessionId?: string;  // 会话ID，用于复用会话
}

// 存档交易记录
export interface SaveTradeRecord {
  orderId: string;
  code: string;
  orderType: string;
  price: number;
  quantity: number;
  fee: number;
  timestamp: string;
}

// 存档每日快照
export interface SaveDailySnapshot {
  date: string;
  totalAssets: number;
  cash: number;
  marketValue: number;
  dailyReturn: number;
  dailyProfit: number;
  cumulativeReturn: number;
}

// 完整存档数据
export interface SaveData {
  version: string;      // 存档版本号
  id: string;           // 存档ID
  name: string;         // 存档名称
  createdAt: string;    // 创建时间
  updatedAt: string;    // 最后更新时间
  config: SaveConfig;
  account: SaveAccountState;
  gameState: SaveGameState;
  stockCodes: string[];
  tradeHistory: SaveTradeRecord[];
  assetHistory: SaveDailySnapshot[];
  pendingOrders: SavePendingOrder[];
}

// 存档挂单记录
export interface SavePendingOrder {
  orderId: string;
  code: string;
  orderType: string;
  price: number;
  quantity: number;
  frozenCash: number;
  frozenQuantity: number;
  orderDate: string;
}

// 存档 API 请求类型
export interface CreateSaveRequest {
  name: string;
  initialCash?: number;
}

export interface UpdateSaveRequest {
  account?: SaveAccountState;
  gameState?: SaveGameState;
  stockCodes?: string[];
  tradeHistory?: SaveTradeRecord[];
  assetHistory?: SaveDailySnapshot[];
  pendingOrders?: SavePendingOrder[];
}

export interface AddStockRequest {
  stockCode: string;
}

// 存档 API 响应类型
export interface DeleteSaveResponse {
  success: boolean;
  message: string;
}

export interface AddStockResponse {
  success: boolean;
  message: string;
  stockCode: string;
}


// ============ 成就系统类型 ============

// 成就稀有度
export type AchievementRarity = 'common' | 'rare' | 'epic' | 'legendary';

// 成就分类
export type AchievementCategory = 'trading' | 'profit' | 'milestone' | 'streak' | 't_trade' | 'special' | 'challenge';

// 进度类型
export type ProgressType = 'boolean' | 'count' | 'percentage' | 'amount';

// 游戏模式
export type GameMode = 'free' | 'challenge';

// 挑战难度
export type ChallengeDifficulty = 'easy' | 'medium' | 'hard';

// 成就定义
export interface AchievementDefinition {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: AchievementCategory;
  rarity: AchievementRarity;
  progressType: ProgressType;
  targetValue: number;
}

// 已解锁成就
export interface UnlockedAchievement {
  achievementId: string;
  unlockedAt: string;
}

// 成就进度
export interface AchievementProgress {
  unlockedAchievements: UnlockedAchievement[];
  progressMap: Record<string, number>;
  newAchievements: string[];
  totalUnlocked: number;
  totalAchievements: number;
}

// 检查成就响应
export interface CheckAchievementsResponse {
  newAchievements: string[];
  progress: AchievementProgress;
}

// ============ 做T统计类型 ============

// 做T记录
export interface TTradeRecord {
  id: string;
  stockCode: string;
  sellPrice: number;
  buyPrice: number;
  quantity: number;
  sellFee: number;
  buyFee: number;
  profit: number;
  tradeDate: string;
  sellTime: string;
  buyTime: string;
  isSuccessful: boolean;
}

// 做T统计
export interface TTradeStatistics {
  totalTrades: number;
  successfulTrades: number;
  failedTrades: number;
  successRate: number;
  totalProfit: number;
  totalFees: number;
  bestTradeProfit: number;
  worstTradeLoss: number;
  averageProfit: number;
}

// 做T历史响应
export interface TTradeHistoryResponse {
  statistics: TTradeStatistics;
  trades: TTradeRecord[];
}

// ============ 挑战模式类型 ============

// 挑战配置
export interface ChallengeConfig {
  id: string;
  name: string;
  difficulty: ChallengeDifficulty;
  stockCode: string;
  stockName: string;
  startDate: string;
  endDate: string;
  initialCash: number;
  targetAssets: number;
  description: string;
}

// 挑战进度
export interface ChallengeProgress {
  challengeId: string;
  currentAssets: number;
  targetAssets: number;
  progressPct: number;
  daysRemaining: number;
  currentDate: string;
}

// 挑战结果
export interface ChallengeResult {
  challengeId: string;
  passed: boolean;
  finalAssets: number;
  targetAssets: number;
  returnPct: number;
  completionDate: string;
}

// 创建挑战请求
export interface CreateChallengeRequest {
  name: string;
  challengeId: string;
}

// 创建挑战响应
export interface CreateChallengeResponse {
  saveId: string;
  challenge: ChallengeConfig;
}

// ============ 排行榜类型 ============

// 排行榜类型
export type LeaderboardType = 
  | 'total_assets' 
  | 'total_return' 
  | 'achievement_count' 
  | 't_trade_profit' 
  | 'win_rate' 
  | 'trade_count';

// 排行榜条目
export interface LeaderboardEntry {
  rank: number;
  saveId: string;
  saveName: string;
  value: number;
  achievementCount: number;
  isCurrent: boolean;
}

// 排行榜响应
export interface LeaderboardResponse {
  type: LeaderboardType;
  entries: LeaderboardEntry[];
}

// 所有排行榜响应
export interface AllLeaderboardsResponse {
  leaderboards: Record<LeaderboardType, LeaderboardEntry[]>;
}

// 存档排名响应
export interface SaveRankResponse {
  saveId: string;
  type: LeaderboardType;
  rank: number | null;
}

// ============ 扩展存档类型 ============

// 扩展存档配置（包含游戏模式）
export interface ExtendedSaveConfig extends SaveConfig {
  gameMode: GameMode;
  challengeId?: string;
}

// 扩展存档数据（包含成就和做T数据）
export interface ExtendedSaveData extends SaveData {
  config: ExtendedSaveConfig;
  achievementProgress?: AchievementProgress;
  tTradeStatistics?: TTradeStatistics;
  challengeConfig?: ChallengeConfig;
  challengeResults?: ChallengeResult[];
}

// 创建存档请求（扩展）
export interface ExtendedCreateSaveRequest extends CreateSaveRequest {
  gameMode?: GameMode;
  challengeId?: string;
}
