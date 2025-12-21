"""集成测试 - 存档系统完整流程测试

Tests:
1. 完整的存档创建-加载-交易-保存流程
2. 存档与交易系统的集成
3. 多存档管理流程

Requirements: 1.1, 2.2, 3.1, 3.2, 4.1, 5.3, 6.2
"""

import json
import shutil
import tempfile
from datetime import date
from pathlib import Path

import pytest

from api.services.save_service import (
    SaveService,
    SaveData,
    SaveNameError,
    SaveNotFoundError,
    AccountState,
    GameState,
)
from src.simulator.simulator import Simulator
from src.trading.models import OrderStatus


class MockDataEngine:
    """Mock DataEngine for integration tests without real API calls."""
    
    def __init__(self, cache_dir: str = "./test_cache"):
        self.cache_dir = cache_dir
        self._daily_data = {}
        self._setup_mock_data()
    
    def _setup_mock_data(self):
        """Setup mock daily data for testing."""
        import pandas as pd
        
        dates = [
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 4),
            date(2024, 1, 5),
            date(2024, 1, 8),
        ]
        
        self._daily_data["600519"] = pd.DataFrame({
            "date": dates,
            "open": [1500.0, 1510.0, 1520.0, 1515.0, 1525.0],
            "high": [1520.0, 1530.0, 1540.0, 1530.0, 1550.0],
            "low": [1490.0, 1500.0, 1510.0, 1505.0, 1515.0],
            "close": [1510.0, 1520.0, 1515.0, 1525.0, 1540.0],
            "volume": [1000000, 1100000, 1050000, 1200000, 1150000],
        })
        
        self._daily_data["000001"] = pd.DataFrame({
            "date": dates,
            "open": [10.0, 10.2, 10.1, 10.3, 10.4],
            "high": [10.5, 10.6, 10.4, 10.6, 10.8],
            "low": [9.8, 10.0, 9.9, 10.1, 10.2],
            "close": [10.2, 10.1, 10.3, 10.4, 10.6],
            "volume": [50000000, 52000000, 48000000, 55000000, 53000000],
        })
    
    def normalize_code(self, code: str) -> tuple[str, str]:
        """Normalize stock code."""
        code = code.strip().lower()
        if code.startswith("sh") or code.startswith("sz"):
            market = code[:2]
            pure_code = code[2:]
        else:
            pure_code = code
            if pure_code.startswith("6"):
                market = "sh"
            else:
                market = "sz"
        return pure_code, market
    
    def get_daily_data(self, code: str, start_date: date, end_date: date, adjust: str = "qfq"):
        """Get mock daily data."""
        import pandas as pd
        
        pure_code, _ = self.normalize_code(code)
        
        if pure_code not in self._daily_data:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
        
        df = self._daily_data[pure_code].copy()
        mask = (df["date"] >= start_date) & (df["date"] <= end_date)
        return df[mask].reset_index(drop=True)
    
    def get_intraday_data(self, code: str, trade_date: date):
        """Get mock intraday data."""
        import pandas as pd
        
        pure_code, _ = self.normalize_code(code)
        
        if pure_code not in self._daily_data:
            return pd.DataFrame(columns=["time", "price", "volume", "turnover_rate"])
        
        df = self._daily_data[pure_code]
        mask = df["date"] == trade_date
        if not mask.any():
            return pd.DataFrame(columns=["time", "price", "volume", "turnover_rate"])
        
        row = df[mask].iloc[0]
        
        times = ["09:30", "10:00", "10:30", "11:00", "11:30",
                 "13:00", "13:30", "14:00", "14:30", "15:00"]
        
        open_price = float(row["open"])
        close_price = float(row["close"])
        prices = [open_price + (close_price - open_price) * i / 9 for i in range(10)]
        
        return pd.DataFrame({
            "time": times,
            "price": prices,
            "volume": [int(row["volume"]) // 10] * 10,
            "turnover_rate": [0.0] * 10,
        })


class TestSaveSystemIntegration:
    """测试存档系统与交易系统的完整集成流程。"""
    
    def test_complete_save_create_load_trade_save_flow(self):
        """
        测试完整的存档创建-加载-交易-保存流程。
        
        Requirements: 1.1, 2.2, 3.1, 3.2, 4.1
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # Step 1: 创建新存档
            save_name = "测试存档"
            initial_cash = 200000.0
            save_data = save_service.create_save(save_name, initial_cash)
            
            assert save_data.name == save_name
            assert save_data.account.cash == initial_cash
            assert save_data.stock_codes == []
            assert save_data.account.positions == []
            
            # Step 2: 添加股票到存档
            save_service.add_stock_to_save(save_data.id, "600519")
            save_service.add_stock_to_save(save_data.id, "000001")
            
            # 验证股票已添加
            loaded_save = save_service.load_save(save_data.id)
            assert "600519" in loaded_save.stock_codes
            assert "000001" in loaded_save.stock_codes
            
            # Step 3: 使用模拟器进行交易
            data_engine = MockDataEngine()
            simulator = Simulator(data_engine, initial_cash=initial_cash)
            
            simulator.setup(
                stock_codes=loaded_save.stock_codes,
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 8)
            )
            
            # 执行买入操作
            current_bars = simulator.get_current_bars()
            buy_order = simulator.trading_engine.submit_buy_order(
                code="600519",
                price=current_bars["600519"].close,
                quantity=100,
                current_date=simulator.current_date,
                current_price=current_bars["600519"].close
            )
            
            assert buy_order.status == OrderStatus.FILLED
            
            # Step 4: 更新存档状态
            # 将模拟器状态保存到存档
            positions_data = []
            for code, pos in simulator.account.positions.items():
                positions_data.append({
                    "code": code,
                    "quantity": pos.quantity,
                    "cost_price": pos.cost_price,
                    "current_price": pos.current_price,
                    "profit_loss": pos.profit_loss,
                    "profit_loss_pct": pos.profit_loss_pct,
                })
            
            loaded_save.account = AccountState(
                cash=simulator.account.cash,
                positions=positions_data
            )
            loaded_save.game_state = GameState(
                current_date=str(simulator.current_date),
                playback_state="paused",
                tick_index=0
            )
            
            save_service.update_save(loaded_save.id, loaded_save)
            
            # Step 5: 重新加载存档验证数据持久化
            final_save = save_service.load_save(save_data.id)
            
            assert final_save.account.cash == simulator.account.cash
            assert len(final_save.account.positions) == 1
            assert final_save.account.positions[0]["code"] == "600519"
            assert final_save.account.positions[0]["quantity"] == 100
            assert final_save.game_state.current_date == str(simulator.current_date)
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_save_load_round_trip_with_trading_state(self):
        """
        测试存档保存和加载的往返一致性（包含交易状态）。
        
        Requirements: 4.1, 4.2, 4.3, 4.4
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档并设置复杂状态
            save_data = save_service.create_save("Round Trip Test", 150000.0)
            
            # 添加股票
            save_service.add_stock_to_save(save_data.id, "600519")
            
            # 设置复杂的账户状态
            save_data = save_service.load_save(save_data.id)
            save_data.account = AccountState(
                cash=50000.0,
                positions=[{
                    "code": "600519",
                    "quantity": 100,
                    "cost_price": 1000.0,
                    "current_price": 1050.0,
                    "profit_loss": 5000.0,
                    "profit_loss_pct": 5.0,
                }]
            )
            save_data.game_state = GameState(
                current_date="2024-01-05",
                playback_state="paused",
                tick_index=120
            )
            
            save_service.update_save(save_data.id, save_data)
            
            # 重新加载并验证
            loaded = save_service.load_save(save_data.id)
            
            assert loaded.account.cash == 50000.0
            assert len(loaded.account.positions) == 1
            assert loaded.account.positions[0]["code"] == "600519"
            assert loaded.account.positions[0]["quantity"] == 100
            assert loaded.account.positions[0]["cost_price"] == 1000.0
            assert loaded.game_state.current_date == "2024-01-05"
            assert loaded.game_state.tick_index == 120
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_multiple_saves_management(self):
        """
        测试多存档管理流程。
        
        Requirements: 1.1, 1.2, 2.2, 6.2
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建多个存档
            save1 = save_service.create_save("存档一", 100000.0)
            save2 = save_service.create_save("存档二", 200000.0)
            save3 = save_service.create_save("存档三", 300000.0)
            
            # 验证列表包含所有存档
            saves = save_service.list_saves()
            save_ids = {s.id for s in saves}
            
            assert save1.id in save_ids
            assert save2.id in save_ids
            assert save3.id in save_ids
            assert len(saves) == 3
            
            # 删除一个存档
            save_service.delete_save(save2.id)
            
            # 验证删除后的列表
            saves_after_delete = save_service.list_saves()
            save_ids_after = {s.id for s in saves_after_delete}
            
            assert save1.id in save_ids_after
            assert save2.id not in save_ids_after
            assert save3.id in save_ids_after
            assert len(saves_after_delete) == 2
            
            # 验证删除的存档无法加载
            with pytest.raises(SaveNotFoundError):
                save_service.load_save(save2.id)
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_stock_addition_and_persistence(self):
        """
        测试股票添加和持久化。
        
        Requirements: 3.1, 5.3, 5.4
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save_data = save_service.create_save("Stock Test", 100000.0)
            
            # 验证初始状态无股票
            assert save_data.stock_codes == []
            
            # 添加多只股票
            stocks_to_add = ["600519", "000001", "300750"]
            for stock in stocks_to_add:
                save_service.add_stock_to_save(save_data.id, stock)
            
            # 重新加载验证
            loaded = save_service.load_save(save_data.id)
            
            for stock in stocks_to_add:
                assert stock in loaded.stock_codes
            
            # 验证重复添加不会产生重复
            save_service.add_stock_to_save(save_data.id, "600519")
            loaded_again = save_service.load_save(save_data.id)
            
            assert loaded_again.stock_codes.count("600519") == 1
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_save_validation_on_load(self):
        """
        测试加载时的存档验证。
        
        Requirements: 4.5, 7.4
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建一个有效存档
            save_data = save_service.create_save("Valid Save", 100000.0)
            
            # 验证可以正常加载
            loaded = save_service.load_save(save_data.id)
            assert loaded.name == "Valid Save"
            
            # 创建一个损坏的存档文件
            corrupted_path = save_service.saves_dir / "corrupted.json"
            with open(corrupted_path, "w") as f:
                f.write("{ invalid json content")
            
            # 验证损坏文件无法加载
            from api.services.save_service import SaveValidationError
            with pytest.raises(SaveValidationError):
                save_service.load_save("corrupted")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_save_name_validation(self):
        """
        测试存档名称验证。
        
        Requirements: 2.3, 2.4
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 测试空名称被拒绝
            with pytest.raises(SaveNameError):
                save_service.create_save("", 100000.0)
            
            with pytest.raises(SaveNameError):
                save_service.create_save("   ", 100000.0)
            
            # 测试重复名称被拒绝
            save_service.create_save("Unique Name", 100000.0)
            
            with pytest.raises(SaveNameError):
                save_service.create_save("Unique Name", 200000.0)
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSaveSystemWithSimulator:
    """测试存档系统与模拟器的深度集成。"""
    
    def test_simulator_state_persistence(self):
        """
        测试模拟器状态通过存档系统持久化。
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save_data = save_service.create_save("Simulator State Test", 200000.0)
            save_service.add_stock_to_save(save_data.id, "600519")
            
            # 第一次模拟会话
            data_engine = MockDataEngine()
            simulator1 = Simulator(data_engine, initial_cash=200000.0)
            simulator1.setup(
                stock_codes=["600519"],
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 8)
            )
            
            # 执行交易
            current_bars = simulator1.get_current_bars()
            simulator1.trading_engine.submit_buy_order(
                code="600519",
                price=current_bars["600519"].close,
                quantity=100,
                current_date=simulator1.current_date,
                current_price=current_bars["600519"].close
            )
            
            # 前进到下一天
            simulator1.next_day()
            
            # 保存状态
            save_data = save_service.load_save(save_data.id)
            positions_data = []
            for code, pos in simulator1.account.positions.items():
                positions_data.append({
                    "code": code,
                    "quantity": pos.quantity,
                    "cost_price": pos.cost_price,
                    "current_price": pos.current_price,
                    "profit_loss": pos.profit_loss,
                    "profit_loss_pct": pos.profit_loss_pct,
                })
            
            save_data.account = AccountState(
                cash=simulator1.account.cash,
                positions=positions_data
            )
            save_data.game_state = GameState(
                current_date=str(simulator1.current_date),
                playback_state="paused",
                tick_index=0
            )
            save_service.update_save(save_data.id, save_data)
            
            # 验证保存的状态
            loaded = save_service.load_save(save_data.id)
            
            assert loaded.game_state.current_date == str(simulator1.current_date)
            assert loaded.account.cash == simulator1.account.cash
            assert len(loaded.account.positions) == 1
            assert loaded.account.positions[0]["code"] == "600519"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_trade_history_persistence(self):
        """
        测试交易历史通过存档系统持久化。
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save_data = save_service.create_save("Trade History Test", 200000.0)
            
            # 模拟添加交易记录
            from api.services.save_service import TradeRecord
            
            trade1 = TradeRecord(
                order_id="order_001",
                code="600519",
                order_type="buy",
                price=1510.0,
                quantity=100,
                fee=22.65,
                timestamp="2024-01-02T10:30:00"
            )
            
            trade2 = TradeRecord(
                order_id="order_002",
                code="600519",
                order_type="sell",
                price=1525.0,
                quantity=100,
                fee=175.38,
                timestamp="2024-01-05T14:30:00"
            )
            
            save_data.trade_history = [trade1, trade2]
            save_service.update_save(save_data.id, save_data)
            
            # 重新加载验证
            loaded = save_service.load_save(save_data.id)
            
            assert len(loaded.trade_history) == 2
            assert loaded.trade_history[0].order_id == "order_001"
            assert loaded.trade_history[0].order_type == "buy"
            assert loaded.trade_history[1].order_id == "order_002"
            assert loaded.trade_history[1].order_type == "sell"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSaveFileStructure:
    """测试存档文件结构。"""
    
    def test_save_file_json_structure(self):
        """
        测试存档文件的 JSON 结构。
        
        Requirements: 7.1, 7.2, 7.3
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save_data = save_service.create_save("JSON Structure Test", 100000.0)
            
            # 直接读取文件验证结构
            save_path = save_service._get_save_path(save_data.id)
            
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 验证必需字段
            required_fields = [
                "version", "id", "name", "created_at", "updated_at",
                "config", "account", "game_state", "stock_codes",
                "trade_history", "asset_history"
            ]
            
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # 验证版本号
            assert data["version"] == "1.0"
            
            # 验证 config 结构
            assert "initial_cash" in data["config"]
            
            # 验证 account 结构
            assert "cash" in data["account"]
            assert "positions" in data["account"]
            
            # 验证 game_state 结构
            assert "current_date" in data["game_state"]
            assert "playback_state" in data["game_state"]
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_storage_directory_structure(self):
        """
        测试存储目录结构。
        
        Requirements: 7.1
        """
        temp_dir = tempfile.mkdtemp()
        save_service = SaveService(storage_dir=temp_dir)
        
        try:
            # 验证目录结构已创建
            assert save_service.saves_dir.exists()
            assert save_service.stock_data_dir.exists()
            assert (save_service.stock_data_dir / "daily").exists()
            assert (save_service.stock_data_dir / "intraday").exists()
            
            # 创建存档后验证文件位置
            save_data = save_service.create_save("Directory Test", 100000.0)
            save_path = save_service._get_save_path(save_data.id)
            
            assert save_path.parent == save_service.saves_dir
            assert save_path.suffix == ".json"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

