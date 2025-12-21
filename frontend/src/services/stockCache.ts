/**
 * 股票信息本地缓存服务
 * 使用 localStorage 缓存股票代码和名称，避免重复请求
 */
import type { StockInfo } from '../types';

const CACHE_KEY = 'stock_info_cache';
const CACHE_VERSION = '1';
const SEARCH_HISTORY_KEY = 'stock_search_history';
const MAX_HISTORY_SIZE = 20;

interface CacheData {
  version: string;
  stocks: Record<string, StockInfo>;
  updatedAt: string;
}

export interface CachedStock {
  code: string;
  name: string;
  market: string;
  addedAt: string;
}

// 从 localStorage 加载缓存
function loadCache(): Record<string, StockInfo> {
  try {
    const data = localStorage.getItem(CACHE_KEY);
    if (!data) return {};
    
    const cache: CacheData = JSON.parse(data);
    // 版本不匹配则清空缓存
    if (cache.version !== CACHE_VERSION) {
      localStorage.removeItem(CACHE_KEY);
      return {};
    }
    return cache.stocks || {};
  } catch (e) {
    console.error('Failed to load stock cache:', e);
    return {};
  }
}

// 保存缓存到 localStorage
function saveCache(stocks: Record<string, StockInfo>): void {
  try {
    const cache: CacheData = {
      version: CACHE_VERSION,
      stocks,
      updatedAt: new Date().toISOString(),
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch (e) {
    console.error('Failed to save stock cache:', e);
  }
}

// 内存缓存
let memoryCache: Record<string, StockInfo> = loadCache();

export const stockCache = {
  /**
   * 获取缓存的股票信息
   */
  get(code: string): StockInfo | null {
    return memoryCache[code] || null;
  },

  /**
   * 批量获取缓存的股票信息
   */
  getMany(codes: string[]): { cached: Record<string, StockInfo>; missing: string[] } {
    const cached: Record<string, StockInfo> = {};
    const missing: string[] = [];
    
    for (const code of codes) {
      if (memoryCache[code]) {
        cached[code] = memoryCache[code];
      } else {
        missing.push(code);
      }
    }
    
    return { cached, missing };
  },

  /**
   * 缓存股票信息
   */
  set(code: string, info: StockInfo): void {
    memoryCache[code] = info;
    saveCache(memoryCache);
  },

  /**
   * 批量缓存股票信息
   */
  setMany(stocks: Record<string, StockInfo>): void {
    memoryCache = { ...memoryCache, ...stocks };
    saveCache(memoryCache);
  },

  /**
   * 获取所有缓存的股票信息
   */
  getAll(): Record<string, StockInfo> {
    return { ...memoryCache };
  },

  /**
   * 清空缓存
   */
  clear(): void {
    memoryCache = {};
    localStorage.removeItem(CACHE_KEY);
  },

  /**
   * 获取缓存数量
   */
  size(): number {
    return Object.keys(memoryCache).length;
  },
};

export default stockCache;

// 搜索历史相关函数
export function getSearchHistory(): CachedStock[] {
  try {
    const data = localStorage.getItem(SEARCH_HISTORY_KEY);
    if (!data) return [];
    return JSON.parse(data);
  } catch (e) {
    console.error('Failed to load search history:', e);
    return [];
  }
}

export function addToSearchHistory(stock: StockInfo): void {
  try {
    const history = getSearchHistory();
    // 移除已存在的相同股票
    const filtered = history.filter(h => h.code !== stock.code);
    // 添加到开头
    const newHistory: CachedStock[] = [
      { code: stock.code, name: stock.name, market: stock.market, addedAt: new Date().toISOString() },
      ...filtered,
    ].slice(0, MAX_HISTORY_SIZE);
    localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(newHistory));
    
    // 同时缓存股票信息
    stockCache.set(stock.code, stock);
  } catch (e) {
    console.error('Failed to add to search history:', e);
  }
}

export function removeFromSearchHistory(code: string): void {
  try {
    const history = getSearchHistory();
    const filtered = history.filter(h => h.code !== code);
    localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(filtered));
  } catch (e) {
    console.error('Failed to remove from search history:', e);
  }
}

export function clearSearchHistory(): void {
  localStorage.removeItem(SEARCH_HISTORY_KEY);
}
