"""数据引擎 - Data engine for fetching and caching stock data from AkShare."""

import json
import os
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.data_engine.models import StockInfo
from src.exceptions import (
    DataFetchError,
    InvalidDateRangeError,
    InvalidStockCodeError,
)


class DataEngine:
    """数据引擎类 - Handles stock data fetching and caching."""
    
    def __init__(self, cache_dir: str = "./data_cache"):
        """
        初始化数据引擎，指定缓存目录。

        Args:
            cache_dir: 缓存目录路径，默认为 ./data_cache
        """
        self.cache_dir = Path(cache_dir)
        self._cache_lock = threading.RLock()
        self._stock_list_cache: list[StockInfo] = []
        self._stock_name_map: dict[str, str] | None = None
        self._ensure_cache_dirs()
        self._register_legacy_daily_cache()
    
    def _ensure_cache_dirs(self) -> None:
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "intraday").mkdir(parents=True, exist_ok=True)

    def _manifest_path(self) -> Path:
        """返回日线缓存覆盖清单路径。"""
        return self.cache_dir / "daily_cache_manifest.json"

    def _load_manifest(self) -> dict[str, Any]:
        path = self._manifest_path()
        if not path.exists():
            return {"version": 1, "entries": {}}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data.get("entries"), dict):
                raise ValueError("invalid cache manifest")
            return data
        except (OSError, ValueError, json.JSONDecodeError):
            return {"version": 1, "entries": {}}

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        path = self._manifest_path()
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(path)

    @staticmethod
    def _merge_ranges(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]:
        if not ranges:
            return []
        ordered = sorted(ranges, key=lambda item: item[0])
        merged = [ordered[0]]
        for start, end in ordered[1:]:
            previous_start, previous_end = merged[-1]
            if start <= previous_end + timedelta(days=1):
                merged[-1] = (previous_start, max(previous_end, end))
            else:
                merged.append((start, end))
        return merged

    @staticmethod
    def _missing_ranges(
        start_date: date,
        end_date: date,
        covered_ranges: list[tuple[date, date]],
    ) -> list[tuple[date, date]]:
        missing: list[tuple[date, date]] = []
        cursor = start_date
        for covered_start, covered_end in DataEngine._merge_ranges(covered_ranges):
            if covered_end < cursor:
                continue
            if covered_start > end_date:
                break
            if covered_start > cursor:
                missing.append((cursor, min(end_date, covered_start - timedelta(days=1))))
            cursor = max(cursor, covered_end + timedelta(days=1))
            if cursor > end_date:
                break
        if cursor <= end_date:
            missing.append((cursor, end_date))
        return missing

    def _manifest_ranges(self, code: str, adjust: str) -> list[tuple[date, date]]:
        manifest = self._load_manifest()
        entry = manifest["entries"].get(f"{code}:{adjust or 'raw'}", {})
        ranges = []
        for item in entry.get("ranges", []):
            try:
                ranges.append((date.fromisoformat(item["start"]), date.fromisoformat(item["end"])))
            except (KeyError, TypeError, ValueError):
                continue
        return self._merge_ranges(ranges)

    def _record_cached_range(
        self,
        code: str,
        start_date: date,
        end_date: date,
        adjust: str,
    ) -> None:
        with self._cache_lock:
            manifest = self._load_manifest()
            key = f"{code}:{adjust or 'raw'}"
            entry = manifest["entries"].get(key, {})
            ranges = self._manifest_ranges(code, adjust)
            ranges.append((start_date, end_date))
            entry.update({
                "code": code,
                "adjust": adjust or "raw",
                "updated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
                "ranges": [
                    {"start": start.isoformat(), "end": end.isoformat()}
                    for start, end in self._merge_ranges(ranges)
                ],
            })
            manifest["entries"][key] = entry
            self._save_manifest(manifest)

    def _register_legacy_daily_cache(self) -> None:
        """把旧版只有 CSV、没有覆盖清单的日线缓存纳入管理。"""
        manifest = self._load_manifest()
        known_keys = set(manifest["entries"])
        for path in self.cache_dir.glob("*.csv"):
            if path.name == "stock_list.csv":
                continue
            stem_parts = path.stem.rsplit("_", 1)
            if len(stem_parts) != 2:
                continue
            code, adjust = stem_parts
            if not (code.isdigit() and len(code) == 6):
                continue
            key = f"{code}:{adjust}"
            if key in known_keys:
                continue
            try:
                frame = pd.read_csv(path, usecols=["date"])
                parsed = pd.to_datetime(frame["date"], errors="raise").dt.date
                if parsed.empty:
                    continue
                self._record_cached_range(code, min(parsed), max(parsed), adjust)
                known_keys.add(key)
            except Exception:
                continue
    
    def normalize_code(self, code: str) -> tuple[str, str]:
        """
        统一股票代码格式，处理 sh/sz 前缀。
        
        Args:
            code: 股票代码，可以是 "600519", "sh600519", "SH600519" 等格式
            
        Returns:
            tuple: (纯数字代码, 市场标识) 如 ("600519", "sh")
            
        Raises:
            InvalidStockCodeError: 当股票代码格式无效时
        """
        code = code.strip().lower()
        
        # 处理带前缀的代码
        if code.startswith("sh") or code.startswith("sz"):
            market = code[:2]
            pure_code = code[2:]
        else:
            pure_code = code
            # 根据代码规则判断市场
            # 6开头为上海，0/3开头为深圳
            if pure_code.startswith("6"):
                market = "sh"
            elif pure_code.startswith("0") or pure_code.startswith("3"):
                market = "sz"
            else:
                raise InvalidStockCodeError(f"无法识别的股票代码格式: {code}")
        
        # 验证纯数字代码
        if not pure_code.isdigit() or len(pure_code) != 6:
            raise InvalidStockCodeError(f"无效的股票代码: {code}，代码必须是6位数字")
        
        return pure_code, market
    
    def get_stock_list(self) -> list[StockInfo]:
        """
        获取所有 A 股股票列表。

        优先级：内存缓存 → 当日磁盘缓存 → 东方财富接口 → 交易所官网接口。

        Returns:
            list[StockInfo]: 股票信息列表

        Raises:
            DataFetchError: 当所有数据源均失败时
        """
        # 内存缓存（进程生命周期内有效）
        if self._stock_list_cache:
            return self._stock_list_cache

        # 当日磁盘缓存
        cached = self._load_stock_list_cache()
        if cached:
            self._stock_list_cache = cached
            return cached

        errors = []

        # 数据源1：东方财富
        try:
            import akshare as ak

            df = ak.stock_zh_a_spot_em()
            stock_list = self._build_stock_list(df, code_col="代码", name_col="名称")
            if stock_list:
                self._stock_list_cache = stock_list
                self._save_stock_list_cache(stock_list)
                return stock_list
        except Exception as e:
            errors.append(f"东方财富: {str(e)}")

        # 数据源2：交易所官网（上交所/深交所）
        try:
            import akshare as ak

            df = ak.stock_info_a_code_name()
            stock_list = self._build_stock_list(df, code_col="code", name_col="name")
            if stock_list:
                self._stock_list_cache = stock_list
                self._save_stock_list_cache(stock_list)
                return stock_list
        except Exception as e:
            errors.append(f"交易所官网: {str(e)}")

        raise DataFetchError(f"获取股票列表失败: {'; '.join(errors)}")

    @staticmethod
    def _build_stock_list(df: pd.DataFrame, code_col: str, name_col: str) -> list[StockInfo]:
        """从 DataFrame 构建股票列表，跳过北交所等无法识别的代码。"""
        stock_list = []
        for _, row in df.iterrows():
            code = str(row[code_col]).zfill(6)
            name = str(row[name_col])

            if code.startswith("6"):
                market = "sh"
            elif code.startswith("0") or code.startswith("3"):
                market = "sz"
            else:
                continue

            stock_list.append(StockInfo(code=code, name=name, market=market))
        return stock_list

    def _stock_list_cache_path(self) -> Path:
        return self.cache_dir / "stock_list.csv"

    def _load_stock_list_cache(self) -> list[StockInfo]:
        """加载当日有效的股票列表磁盘缓存。"""
        import datetime as _dt

        path = self._stock_list_cache_path()
        if not path.exists():
            return []
        try:
            mtime = _dt.date.fromtimestamp(path.stat().st_mtime)
            if mtime != _dt.date.today():
                return []
            df = pd.read_csv(path, dtype={"code": str})
            return [
                StockInfo(code=str(r["code"]).zfill(6), name=str(r["name"]), market=str(r["market"]))
                for _, r in df.iterrows()
            ]
        except Exception:
            return []

    def _save_stock_list_cache(self, stock_list: list[StockInfo]) -> None:
        try:
            pd.DataFrame(
                [{"code": s.code, "name": s.name, "market": s.market} for s in stock_list]
            ).to_csv(self._stock_list_cache_path(), index=False)
            self._stock_name_map = {stock.code: stock.name for stock in stock_list}
        except Exception:
            pass

    def get_cached_stock_name(self, code: str) -> Optional[str]:
        """从本地股票列表读取名称，不为展示名称触发网络请求。"""
        pure_code, _ = self.normalize_code(code)
        if self._stock_name_map is None:
            self._stock_name_map = {}
            path = self._stock_list_cache_path()
            if path.exists():
                try:
                    frame = pd.read_csv(path, dtype={"code": str}, usecols=["code", "name"])
                    self._stock_name_map = {
                        str(row["code"]).zfill(6): str(row["name"])
                        for _, row in frame.iterrows()
                    }
                except Exception:
                    self._stock_name_map = {}
        return self._stock_name_map.get(pure_code)
    
    def get_daily_data(
        self,
        code: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取股票日线数据。
        
        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
            adjust: 复权类型，默认 "qfq" (前复权)
            
        Returns:
            DataFrame: 包含 date, open, high, low, close, volume 列
            
        Raises:
            InvalidStockCodeError: 当股票代码无效时
            InvalidDateRangeError: 当日期范围无效时
            DataFetchError: 当数据获取失败时
        """
        # 验证日期范围
        if start_date > end_date:
            raise InvalidDateRangeError(
                f"起始日期 {start_date} 不能晚于结束日期 {end_date}"
            )
        
        self.ensure_daily_cache(code, start_date, end_date, adjust)
        return self.get_cached_daily_data(code, start_date, end_date, adjust)

    def get_cached_daily_data(
        self,
        code: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq",
        require_complete: bool = True,
    ) -> pd.DataFrame:
        """只读本地日线缓存，不触发任何网络请求。"""
        if start_date > end_date:
            raise InvalidDateRangeError(
                f"起始日期 {start_date} 不能晚于结束日期 {end_date}"
            )
        pure_code, _ = self.normalize_code(code)
        status = self.get_cache_status(pure_code, start_date, end_date, adjust)
        if require_complete and not status["complete"]:
            gaps = ", ".join(
                f"{item['start']} 至 {item['end']}" for item in status["missing_ranges"]
            )
            raise DataFetchError(f"本地缓存不完整，缺少：{gaps}")

        cached = self._load_from_cache(pure_code, start_date, end_date, adjust)
        if cached is None:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        return cached

    def ensure_daily_cache(
        self,
        code: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq",
    ) -> dict[str, Any]:
        """显式下载并补齐指定区间，返回下载后的覆盖状态。"""
        if start_date > end_date:
            raise InvalidDateRangeError(
                f"起始日期 {start_date} 不能晚于结束日期 {end_date}"
            )
        pure_code, market = self.normalize_code(code)
        missing = self._missing_ranges(
            start_date,
            end_date,
            self._manifest_ranges(pure_code, adjust),
        )

        for gap_start, gap_end in missing:
            try:
                df = self._fetch_daily_from_eastmoney(
                    pure_code, gap_start, gap_end, adjust
                )
            except InvalidStockCodeError:
                raise
            except Exception as em_error:
                try:
                    df = self._fetch_daily_from_tencent(
                        pure_code, market, gap_start, gap_end, adjust
                    )
                except Exception as tx_error:
                    raise DataFetchError(
                        f"获取股票 {code} 日线数据失败: "
                        f"东方财富接口: {str(em_error)}; 腾讯接口: {str(tx_error)}"
                    ) from tx_error

            if not df.empty:
                self._save_to_cache(pure_code, df, adjust)
            # 数据源已成功回答该请求。区间内可能只有周末、停牌日或尚未上市日期，
            # 因此覆盖清单记录“已查询区间”，不能只根据 CSV 首尾日期推断。
            self._record_cached_range(pure_code, gap_start, gap_end, adjust)

        return self.get_cache_status(pure_code, start_date, end_date, adjust)

    def get_cache_status(
        self,
        code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        adjust: str = "qfq",
    ) -> dict[str, Any]:
        """返回单只股票的本地日线覆盖范围和请求缺口。"""
        pure_code, _ = self.normalize_code(code)
        ranges = self._manifest_ranges(pure_code, adjust)
        missing: list[tuple[date, date]] = []
        if start_date is not None and end_date is not None:
            if start_date > end_date:
                raise InvalidDateRangeError(
                    f"起始日期 {start_date} 不能晚于结束日期 {end_date}"
                )
            missing = self._missing_ranges(start_date, end_date, ranges)

        cache_path = self._get_cache_path(pure_code, adjust)
        row_count = 0
        data_start = None
        data_end = None
        if cache_path.exists():
            try:
                df = pd.read_csv(cache_path, usecols=["date"])
                if not df.empty:
                    parsed = pd.to_datetime(df["date"]).dt.date
                    row_count = len(df)
                    data_start = min(parsed).isoformat()
                    data_end = max(parsed).isoformat()
            except Exception:
                pass

        return {
            "code": pure_code,
            "name": self.get_cached_stock_name(pure_code),
            "adjust": adjust or "raw",
            "complete": not missing if start_date is not None and end_date is not None else bool(ranges),
            "ranges": [
                {"start": range_start.isoformat(), "end": range_end.isoformat()}
                for range_start, range_end in ranges
            ],
            "missing_ranges": [
                {"start": gap_start.isoformat(), "end": gap_end.isoformat()}
                for gap_start, gap_end in missing
            ],
            "row_count": row_count,
            "data_start": data_start,
            "data_end": data_end,
            "file_size": cache_path.stat().st_size if cache_path.exists() else 0,
        }

    def list_daily_cache(self) -> list[dict[str, Any]]:
        """列出所有由覆盖清单管理的日线缓存。"""
        manifest = self._load_manifest()
        result = []
        for entry in manifest["entries"].values():
            code = entry.get("code")
            adjust = entry.get("adjust", "qfq")
            if not code:
                continue
            status = self.get_cache_status(code, adjust=adjust)
            status["updated_at"] = entry.get("updated_at")
            result.append(status)
        return sorted(result, key=lambda item: (item["code"], item["adjust"]))

    def delete_daily_cache(self, code: str, adjust: str = "qfq") -> bool:
        """删除单只股票指定复权方式的日线缓存及覆盖记录。"""
        pure_code, _ = self.normalize_code(code)
        with self._cache_lock:
            path = self._get_cache_path(pure_code, adjust)
            existed = path.exists()
            path.unlink(missing_ok=True)

            manifest = self._load_manifest()
            key = f"{pure_code}:{adjust or 'raw'}"
            existed = manifest["entries"].pop(key, None) is not None or existed
            self._save_manifest(manifest)
            return existed

    def _fetch_daily_from_eastmoney(
        self,
        pure_code: str,
        start_date: date,
        end_date: date,
        adjust: str
    ) -> pd.DataFrame:
        """从东方财富接口获取日线数据（AkShare stock_zh_a_hist）。"""
        import akshare as ak

        df = ak.stock_zh_a_hist(
            symbol=pure_code,
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust=adjust
        )

        if df.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        # 重命名列以匹配设计
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume"
        })

        # 只保留需要的列
        df = df[["date", "open", "high", "low", "close", "volume"]]

        # 确保 date 列是日期类型
        df["date"] = pd.to_datetime(df["date"]).dt.date

        return df

    def _fetch_daily_from_tencent(
        self,
        pure_code: str,
        market: str,
        start_date: date,
        end_date: date,
        adjust: str
    ) -> pd.DataFrame:
        """从腾讯接口获取日线数据（AkShare stock_zh_a_hist_tx），作为东方财富的回退数据源。"""
        import akshare as ak

        df = ak.stock_zh_a_hist_tx(
            symbol=f"{market}{pure_code}",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust=adjust
        )

        if df.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        # 腾讯接口返回列: date, open, close, high, low, amount（成交量，单位: 手）
        df = df.rename(columns={"amount": "volume"})

        df = df[["date", "open", "high", "low", "close", "volume"]]
        df["date"] = pd.to_datetime(df["date"]).dt.date

        return df
    
    def get_intraday_data(
        self,
        code: str,
        trade_date: date
    ) -> pd.DataFrame:
        """
        获取股票日内分时数据。
        
        Args:
            code: 股票代码
            trade_date: 交易日期
            
        Returns:
            DataFrame: 包含 time, price, volume, turnover_rate 列
            如果真实分时数据不可用，基于日线数据模拟生成
        """
        from src.data_engine.models import DailyBar
        
        # 规范化股票代码
        pure_code, market = self.normalize_code(code)
        
        # 尝试从缓存加载分时数据
        cache_path = self._get_intraday_cache_path(pure_code, trade_date)
        if cache_path.exists():
            try:
                df = pd.read_csv(cache_path)
                return df
            except Exception:
                cache_path.unlink(missing_ok=True)
        
        # 尝试从 AkShare 获取真实分时数据
        try:
            import akshare as ak
            
            # 尝试获取分时数据（仅当天或近期数据可用）
            df = ak.stock_zh_a_hist_min_em(
                symbol=pure_code,
                period="1",
                start_date=trade_date.strftime("%Y-%m-%d 09:30:00"),
                end_date=trade_date.strftime("%Y-%m-%d 15:00:00"),
                adjust=""
            )
            
            if not df.empty:
                # 重命名列
                df = df.rename(columns={
                    "时间": "time",
                    "收盘": "price",
                    "成交量": "volume",
                    "换手率": "turnover_rate"
                })
                
                # 提取时间部分
                df["time"] = pd.to_datetime(df["time"]).dt.strftime("%H:%M")
                
                # 只保留需要的列
                if "turnover_rate" not in df.columns:
                    df["turnover_rate"] = 0.0
                
                df = df[["time", "price", "volume", "turnover_rate"]]
                
                # 保存到缓存
                self._save_intraday_to_cache(pure_code, trade_date, df)
                
                return df
                
        except Exception:
            # 真实分时数据不可用，使用模拟数据
            pass
        
        # 获取日线数据用于模拟
        daily_df = self.get_daily_data(code, trade_date, trade_date)
        
        if daily_df.empty:
            return pd.DataFrame(columns=["time", "price", "volume", "turnover_rate"])
        
        # 构建 DailyBar 对象
        row = daily_df.iloc[0]
        daily_bar = DailyBar(
            date=row["date"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"])
        )
        
        # 生成模拟分时数据
        simulated_df = self.generate_simulated_intraday(daily_bar)
        
        # 保存到缓存
        self._save_intraday_to_cache(pure_code, trade_date, simulated_df)
        
        return simulated_df
    
    def generate_simulated_intraday(
        self,
        daily_bar: "DailyBar"
    ) -> pd.DataFrame:
        """
        基于日线数据模拟生成分时走势。
        生成 240 个数据点（9:30-11:30, 13:00-15:00）
        
        Args:
            daily_bar: 日线数据
            
        Returns:
            DataFrame: 模拟的分时数据，包含 time, price, volume, turnover_rate 列
        """
        import numpy as np
        
        # 生成交易时间点（240分钟）
        # 上午: 9:30-11:30 (120分钟)
        # 下午: 13:00-15:00 (120分钟)
        times = []
        
        # 上午时段
        for hour in range(9, 12):
            start_min = 30 if hour == 9 else 0
            end_min = 30 if hour == 11 else 60
            for minute in range(start_min, end_min):
                times.append(f"{hour:02d}:{minute:02d}")
        
        # 下午时段
        for hour in range(13, 15):
            for minute in range(60):
                times.append(f"{hour:02d}:{minute:02d}")
        
        n_points = len(times)  # 应该是 240
        
        # 使用随机游走模拟价格走势
        # 确保：开盘价接近 open，收盘价等于 close，价格在 [low, high] 范围内
        np.random.seed(hash(str(daily_bar.date)) % (2**32))
        
        # 生成随机游走
        returns = np.random.normal(0, 0.001, n_points)
        
        # 计算累积收益
        cumulative = np.cumsum(returns)
        
        # 调整使得起点为开盘价，终点为收盘价
        # 线性插值调整
        adjustment = np.linspace(0, daily_bar.close - daily_bar.open - cumulative[-1] * daily_bar.open, n_points)
        
        prices = daily_bar.open * (1 + cumulative) + adjustment
        
        # 确保第一个价格接近开盘价
        prices[0] = daily_bar.open
        
        # 确保最后一个价格等于收盘价
        prices[-1] = daily_bar.close
        
        # 限制价格在 [low, high] 范围内
        prices = np.clip(prices, daily_bar.low, daily_bar.high)
        
        # 生成成交量分布（通常开盘和收盘时段成交量较大）
        volume_weights = np.ones(n_points)
        # 开盘前30分钟权重较高
        volume_weights[:30] = 1.5
        # 收盘前30分钟权重较高
        volume_weights[-30:] = 1.5
        # 午盘开始时权重较高
        volume_weights[120:135] = 1.3
        
        # 归一化并分配成交量
        volume_weights = volume_weights / volume_weights.sum()
        volumes = (volume_weights * daily_bar.volume).astype(int)
        
        # 确保总成交量等于日线成交量
        diff = daily_bar.volume - volumes.sum()
        volumes[-1] += diff
        
        # 计算换手率（简化处理，假设均匀分布）
        turnover_rates = np.full(n_points, 0.0)
        
        # 构建 DataFrame
        df = pd.DataFrame({
            "time": times,
            "price": np.round(prices, 2),
            "volume": volumes,
            "turnover_rate": turnover_rates
        })
        
        return df
    
    def _save_intraday_to_cache(
        self,
        code: str,
        trade_date: date,
        data: pd.DataFrame
    ) -> None:
        """保存分时数据到缓存"""
        if data.empty:
            return
        
        cache_path = self._get_intraday_cache_path(code, trade_date)
        
        try:
            data.to_csv(cache_path, index=False)
        except Exception:
            pass
    
    def _get_cache_path(self, code: str, adjust: str = "qfq") -> Path:
        """获取日线数据缓存文件路径（按复权方式区分，避免混用）"""
        suffix = adjust if adjust else "raw"
        return self.cache_dir / f"{code}_{suffix}.csv"
    
    def _get_intraday_cache_path(self, code: str, trade_date: date) -> Path:
        """获取分时数据缓存文件路径"""
        return self.cache_dir / "intraday" / f"{code}_{trade_date.isoformat()}.csv"
    
    def _load_from_cache(
        self,
        code: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq"
    ) -> Optional[pd.DataFrame]:
        """
        从本地缓存加载数据。

        Args:
            code: 股票代码（纯数字）
            start_date: 起始日期
            end_date: 结束日期
            adjust: 复权类型（缓存按复权方式区分）

        Returns:
            DataFrame 或 None（如果缓存不存在）
        """
        cache_path = self._get_cache_path(code, adjust)
        
        if not cache_path.exists():
            return None
        
        try:
            df = pd.read_csv(cache_path)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            
            # 筛选日期范围
            mask = (df["date"] >= start_date) & (df["date"] <= end_date)
            filtered_df = df[mask].copy()
            
            # 即使数据不完整也返回已有数据
            # 这样可以避免因为请求未来日期而导致整个数据加载失败
            if not filtered_df.empty:
                return filtered_df.reset_index(drop=True)
            
            return None
            
        except Exception:
            # 缓存文件损坏，删除并返回 None
            cache_path.unlink(missing_ok=True)
            return None
    
    def _save_to_cache(self, code: str, data: pd.DataFrame, adjust: str = "qfq") -> None:
        """
        保存数据到本地缓存。

        Args:
            code: 股票代码（纯数字）
            data: 要保存的数据
            adjust: 复权类型（缓存按复权方式区分）
        """
        if data.empty:
            return

        cache_path = self._get_cache_path(code, adjust)
        
        with self._cache_lock:
            # 如果缓存已存在，合并数据
            if cache_path.exists():
                existing_df = pd.read_csv(cache_path)
                existing_df["date"] = pd.to_datetime(existing_df["date"]).dt.date

                # 合并并去重
                combined = pd.concat([existing_df, data], ignore_index=True)
                combined = combined.drop_duplicates(subset=["date"], keep="last")
                combined = combined.sort_values("date").reset_index(drop=True)
                data = combined

            # 先写临时文件再替换，避免中断时留下半个 CSV。
            temp_path = cache_path.with_suffix(".tmp")
            data.to_csv(temp_path, index=False)
            temp_path.replace(cache_path)
