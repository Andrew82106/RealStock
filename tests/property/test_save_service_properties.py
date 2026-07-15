"""属性测试 - 存档服务模块 Property-based tests for save service module."""

import json
import tempfile
import shutil
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st, assume

from api.services.save_service import (
    SaveService, SaveData, SaveMetadata, SaveConfig, AccountState, GameState,
    SaveNameError, SaveNotFoundError, SaveValidationError, REQUIRED_FIELDS
)


# 测试数据生成策略
@st.composite
def valid_save_name(draw):
    """生成有效的存档名称（非空、非纯空白）"""
    # 生成包含字母、数字、中文的名称
    name = draw(st.text(
        alphabet=st.sampled_from(
            list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-") +
            list("测试存档游戏模拟交易")
        ),
        min_size=1,
        max_size=50
    ))
    # 确保不是纯空白
    assume(name.strip())
    return name


@st.composite
def whitespace_only_name(draw):
    """生成纯空白字符串"""
    return draw(st.text(alphabet=" \t\n\r", min_size=0, max_size=10))


@st.composite
def name_with_special_chars(draw):
    """生成包含特殊字符的名称"""
    base = draw(st.text(
        alphabet=st.sampled_from(list("abcdefghijklmnopqrstuvwxyz测试")),
        min_size=1,
        max_size=20
    ))
    special = draw(st.text(
        alphabet=st.sampled_from(list("!@#$%^&*()+=[]{}|\\:;\"'<>,./?")),
        min_size=1,
        max_size=10
    ))
    return base + special


@st.composite
def valid_initial_cash(draw):
    """生成有效的初始资金"""
    return draw(st.floats(min_value=1000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False))


class TestSaveCreationProducesValidFile:
    """
    Property 3: Save Creation Produces Valid File
    Feature: save-system, Property 3: Save Creation Produces Valid File
    **Validates: Requirements 2.2, 7.1, 7.2, 7.3**
    
    *For any* valid (non-empty, non-duplicate) save name, creating a save SHALL produce 
    a valid JSON file in the storage directory with the correct filename and all required fields.
    """
    
    @settings(max_examples=100)
    @given(name=valid_save_name(), initial_cash=valid_initial_cash())
    def test_save_creation_produces_valid_json_file(self, name: str, initial_cash: float):
        """
        验证创建存档产生有效的 JSON 文件。
        
        *For any* 有效的存档名称和初始资金：
        - 应在存储目录中创建 .json 文件
        - 文件应包含有效的 JSON 数据
        - 文件应包含所有必需字段
        """
        # 为每次测试创建新的临时目录
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save_data = service.create_save(name, initial_cash)
        
            # 验证文件存在
            save_path = service._get_save_path(save_data.id)
            assert save_path.exists(), f"存档文件应存在: {save_path}"
            assert save_path.suffix == ".json", f"存档文件应为 .json 格式"
            
            # 验证文件包含有效 JSON
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 验证所有必需字段存在
            for field in REQUIRED_FIELDS:
                assert field in data, f"存档文件应包含字段: {field}"
            
            # 验证版本号
            assert data["version"] == "1.0", "存档版本应为 1.0"
            
            # 验证名称保存正确
            assert data["name"] == name.strip(), f"存档名称应为 {name.strip()}"
            
            # 验证初始资金
            assert data["config"]["initial_cash"] == initial_cash, f"初始资金应为 {initial_cash}"
            assert data["account"]["cash"] == initial_cash, f"账户现金应为 {initial_cash}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=valid_save_name())
    def test_save_file_in_correct_directory(self, name: str):
        """
        验证存档文件创建在正确的目录中。
        
        *For any* 有效的存档名称：
        存档文件应创建在 storage/saves/ 目录下
        """
        # 为每次测试创建新的临时目录
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            save_data = service.create_save(name)
            
            save_path = service._get_save_path(save_data.id)
            assert save_path.parent == service.saves_dir, \
                f"存档文件应在 saves 目录下: {save_path.parent} != {service.saves_dir}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestFilenameSanitization:
    """
    Property 11: Filename Sanitization
    Feature: save-system, Property 11: Filename Sanitization
    **Validates: Requirements 7.2**
    
    *For any* save name containing special characters, the resulting filename SHALL only 
    contain safe characters (alphanumeric, hyphen, underscore, Chinese characters) 
    and SHALL have .json extension.
    """
    
    @settings(max_examples=100)
    @given(name=name_with_special_chars())
    def test_sanitized_filename_contains_only_safe_chars(self, name: str):
        """
        验证清理后的文件名只包含安全字符。
        
        *For any* 包含特殊字符的名称：
        清理后的文件名应只包含字母、数字、下划线、连字符和中文字符
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            sanitized = service.sanitize_filename(name)
            
            # 验证只包含安全字符
            import re
            safe_pattern = r'^[\w\u4e00-\u9fff-]+$'
            assert re.match(safe_pattern, sanitized), \
                f"清理后的文件名应只包含安全字符: '{sanitized}' (原名: '{name}')"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=st.text(min_size=1, max_size=100))
    def test_sanitized_filename_never_empty_for_nonempty_input(self, name: str):
        """
        验证非空输入产生非空文件名。
        
        *For any* 非空字符串：
        清理后的文件名应非空（可能使用时间戳作为后备）
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            sanitized = service.sanitize_filename(name)
            assert sanitized, f"清理后的文件名不应为空 (原名: '{name}')"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=valid_save_name())
    def test_save_file_has_json_extension(self, name: str):
        """
        验证存档文件有 .json 扩展名。
        
        *For any* 有效的存档名称：
        创建的存档文件应有 .json 扩展名
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            save_data = service.create_save(name)
            save_path = service._get_save_path(save_data.id)
            
            assert save_path.suffix == ".json", \
                f"存档文件应有 .json 扩展名: {save_path}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=name_with_special_chars())
    def test_special_chars_removed_from_filename(self, name: str):
        """
        验证特殊字符从文件名中移除。
        
        *For any* 包含特殊字符的名称：
        清理后的文件名不应包含特殊字符
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            sanitized = service.sanitize_filename(name)
            
            special_chars = "!@#$%^&*()+=[]{}|\\:;\"'<>,./?"
            for char in special_chars:
                assert char not in sanitized, \
                    f"清理后的文件名不应包含特殊字符 '{char}': '{sanitized}'"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)



class TestEmptyNameRejection:
    """
    Property 4: Empty Name Rejection
    Feature: save-system, Property 4: Empty Name Rejection
    **Validates: Requirements 2.3**
    
    *For any* string composed entirely of whitespace (including empty string), 
    attempting to create a save SHALL be rejected with an error.
    """
    
    @settings(max_examples=100)
    @given(name=whitespace_only_name())
    def test_empty_or_whitespace_name_rejected(self, name: str):
        """
        验证空名称或纯空白名称被拒绝。
        
        *For any* 空字符串或纯空白字符串：
        创建存档应抛出 SaveNameError
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            with pytest.raises(SaveNameError):
                service.create_save(name)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_none_name_rejected(self):
        """
        验证 None 名称被拒绝。
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            with pytest.raises((SaveNameError, TypeError, AttributeError)):
                service.create_save(None)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestDuplicateNameRejection:
    """
    Property 5: Duplicate Name Rejection
    Feature: save-system, Property 5: Duplicate Name Rejection
    **Validates: Requirements 2.4**
    
    *For any* existing save name, attempting to create another save with 
    the same name SHALL be rejected with an error.
    """
    
    @settings(max_examples=100)
    @given(name=valid_save_name())
    def test_duplicate_name_rejected(self, name: str):
        """
        验证重复名称被拒绝。
        
        *For any* 已存在的存档名称：
        再次创建同名存档应抛出 SaveNameError
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 第一次创建应成功
            service.create_save(name)
            
            # 第二次创建应失败
            with pytest.raises(SaveNameError):
                service.create_save(name)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=valid_save_name())
    def test_duplicate_name_with_different_cash_rejected(self, name: str):
        """
        验证即使初始资金不同，重复名称也被拒绝。
        
        *For any* 已存在的存档名称：
        使用不同初始资金创建同名存档也应被拒绝
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            service.create_save(name, 100000.0)
            
            with pytest.raises(SaveNameError):
                service.create_save(name, 200000.0)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestNewSaveHasEmptyPortfolio:
    """
    Property 6: New Save Has Empty Portfolio
    Feature: save-system, Property 6: New Save Has Empty Portfolio
    **Validates: Requirements 2.5**
    
    *For any* newly created save, the stockCodes list SHALL be empty 
    and positions SHALL be empty.
    """
    
    @settings(max_examples=100)
    @given(name=valid_save_name(), initial_cash=valid_initial_cash())
    def test_new_save_has_empty_stock_codes(self, name: str, initial_cash: float):
        """
        验证新存档的股票代码列表为空。
        
        *For any* 新创建的存档：
        stock_codes 列表应为空
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            save_data = service.create_save(name, initial_cash)
            
            assert save_data.stock_codes == [], \
                f"新存档的 stock_codes 应为空: {save_data.stock_codes}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=valid_save_name(), initial_cash=valid_initial_cash())
    def test_new_save_has_empty_positions(self, name: str, initial_cash: float):
        """
        验证新存档的持仓列表为空。
        
        *For any* 新创建的存档：
        positions 列表应为空
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            save_data = service.create_save(name, initial_cash)
            
            assert save_data.account.positions == [], \
                f"新存档的 positions 应为空: {save_data.account.positions}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=valid_save_name(), initial_cash=valid_initial_cash())
    def test_new_save_has_empty_trade_history(self, name: str, initial_cash: float):
        """
        验证新存档的交易历史为空。
        
        *For any* 新创建的存档：
        trade_history 列表应为空
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            save_data = service.create_save(name, initial_cash)
            
            assert save_data.trade_history == [], \
                f"新存档的 trade_history 应为空: {save_data.trade_history}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)



@st.composite
def valid_save_data(draw):
    """生成有效的 SaveData 对象"""
    name = draw(valid_save_name())
    initial_cash = draw(valid_initial_cash())
    
    # 生成随机股票代码列表
    stock_codes = draw(st.lists(
        st.sampled_from(["600519", "000001", "300750", "601318", "002594"]),
        min_size=0,
        max_size=5,
        unique=True
    ))
    
    return {
        "name": name,
        "initial_cash": initial_cash,
        "stock_codes": stock_codes
    }


class TestSaveLoadRoundTrip:
    """
    Property 1: Save-Load Round Trip
    Feature: save-system, Property 1: Save-Load Round Trip
    **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    
    *For any* valid save data, saving to a file and then loading from that file 
    SHALL produce an equivalent SaveData object.
    """
    
    @settings(max_examples=100)
    @given(data=valid_save_data())
    def test_save_load_round_trip(self, data: dict):
        """
        验证存档保存后加载得到等价数据。
        
        *For any* 有效的存档数据：
        保存后加载应得到等价的 SaveData 对象
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save_data = service.create_save(data["name"], data["initial_cash"])
            
            # 添加股票代码
            for code in data["stock_codes"]:
                save_data.stock_codes.append(code)
            service.update_save(save_data.id, save_data)
            
            # 加载存档
            loaded = service.load_save(save_data.id)
            
            # 验证等价性
            assert loaded.id == save_data.id, "ID 不匹配"
            assert loaded.name == save_data.name, "名称不匹配"
            assert loaded.version == save_data.version, "版本不匹配"
            assert loaded.config.initial_cash == save_data.config.initial_cash, "初始资金不匹配"
            assert loaded.account.cash == save_data.account.cash, "现金不匹配"
            assert loaded.stock_codes == save_data.stock_codes, "股票代码不匹配"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(data=valid_save_data())
    def test_double_round_trip(self, data: dict):
        """
        验证双重 round-trip 后数据仍然等价。
        
        *For any* 有效的存档数据：
        两次保存/加载后应与原数据等价
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 第一次 round-trip
            save1 = service.create_save(data["name"], data["initial_cash"])
            loaded1 = service.load_save(save1.id)
            
            # 更新并保存
            service.update_save(loaded1.id, loaded1)
            
            # 第二次加载
            loaded2 = service.load_save(save1.id)
            
            assert loaded2.id == save1.id, "双重 round-trip 后 ID 不匹配"
            assert loaded2.name == save1.name, "双重 round-trip 后名称不匹配"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSaveListCompleteness:
    """
    Property 2: Save List Completeness
    Feature: save-system, Property 2: Save List Completeness
    **Validates: Requirements 1.1, 1.2**
    
    *For any* set of save files in the storage directory, listing saves SHALL return 
    metadata for all and only those saves, with all required fields populated.
    """
    
    @settings(max_examples=50)
    # Windows 文件系统大小写不敏感，存档名需按小写去重，否则 "H" 和 "h" 会指向同一文件
    @given(names=st.lists(valid_save_name(), min_size=1, max_size=5, unique_by=lambda n: n.lower()))
    def test_list_saves_returns_all_saves(self, names: list[str]):
        """
        验证列出存档返回所有存档。
        
        *For any* 存储目录中的存档文件集合：
        list_saves 应返回所有存档的元数据
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建多个存档
            created_ids = set()
            for name in names:
                save = service.create_save(name)
                created_ids.add(save.id)
            
            # 列出存档
            saves = service.list_saves()
            listed_ids = {s.id for s in saves}
            
            # 验证完整性
            assert created_ids == listed_ids, \
                f"存档列表不完整: 创建 {created_ids}, 列出 {listed_ids}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=50)
    # Windows 文件系统大小写不敏感，存档名需按小写去重，否则 "H" 和 "h" 会指向同一文件
    @given(names=st.lists(valid_save_name(), min_size=1, max_size=5, unique_by=lambda n: n.lower()))
    def test_list_saves_has_required_fields(self, names: list[str]):
        """
        验证存档元数据包含所有必需字段。
        
        *For any* 存档元数据：
        应包含 id, name, created_at, updated_at, current_date 字段
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            for name in names:
                service.create_save(name)
            
            saves = service.list_saves()
            
            for save in saves:
                assert save.id, "id 字段不应为空"
                assert save.name, "name 字段不应为空"
                assert save.created_at, "created_at 字段不应为空"
                assert save.updated_at, "updated_at 字段不应为空"
                # current_date 可以为空（新存档）
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSaveDeletionRemovesFile:
    """
    Property 10: Save Deletion Removes File
    Feature: save-system, Property 10: Save Deletion Removes File
    **Validates: Requirements 6.2, 6.3**
    
    *For any* existing save, after deletion, the save file SHALL no longer exist 
    in the storage directory and SHALL not appear in the save list.
    """
    
    @settings(max_examples=100)
    @given(name=valid_save_name())
    def test_delete_removes_file(self, name: str):
        """
        验证删除存档移除文件。
        
        *For any* 已存在的存档：
        删除后文件应不存在
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save = service.create_save(name)
            save_path = service._get_save_path(save.id)
            
            # 验证文件存在
            assert save_path.exists(), "存档文件应存在"
            
            # 删除存档
            service.delete_save(save.id)
            
            # 验证文件不存在
            assert not save_path.exists(), "删除后存档文件应不存在"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=valid_save_name())
    def test_delete_removes_from_list(self, name: str):
        """
        验证删除存档从列表中移除。
        
        *For any* 已存在的存档：
        删除后不应出现在存档列表中
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save = service.create_save(name)
            
            # 验证在列表中
            saves_before = service.list_saves()
            assert any(s.id == save.id for s in saves_before), "存档应在列表中"
            
            # 删除存档
            service.delete_save(save.id)
            
            # 验证不在列表中
            saves_after = service.list_saves()
            assert not any(s.id == save.id for s in saves_after), "删除后存档不应在列表中"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=valid_save_name())
    def test_delete_nonexistent_raises_error(self, name: str):
        """
        验证删除不存在的存档抛出错误。
        
        *For any* 不存在的存档 ID：
        删除应抛出 SaveNotFoundError
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            with pytest.raises(SaveNotFoundError):
                service.delete_save("nonexistent_save_id")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)



class TestStockAdditionPersistence:
    """
    Property 7: Stock Addition Persistence
    Feature: save-system, Property 7: Stock Addition Persistence
    **Validates: Requirements 3.1, 5.3, 5.4**
    
    *For any* save and any valid stock code, after adding the stock, 
    the save file SHALL contain that stock code in the stockCodes list.
    """
    
    @settings(max_examples=100)
    @given(
        name=valid_save_name(),
        stock_code=st.sampled_from(["600519", "000001", "300750", "601318", "002594"])
    )
    def test_stock_addition_persisted(self, name: str, stock_code: str):
        """
        验证添加股票后持久化到存档。
        
        *For any* 存档和有效股票代码：
        添加后存档文件应包含该股票代码
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建存档
            save = service.create_save(name)
            
            # 添加股票
            service.add_stock_to_save(save.id, stock_code)
            
            # 重新加载验证
            loaded = service.load_save(save.id)
            assert stock_code in loaded.stock_codes, \
                f"股票代码 {stock_code} 应在存档中"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=50)
    @given(
        name=valid_save_name(),
        stock_codes=st.lists(
            st.sampled_from(["600519", "000001", "300750", "601318", "002594"]),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    def test_multiple_stocks_persisted(self, name: str, stock_codes: list[str]):
        """
        验证添加多个股票后全部持久化。
        
        *For any* 存档和多个有效股票代码：
        添加后存档文件应包含所有股票代码
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            save = service.create_save(name)
            
            for code in stock_codes:
                service.add_stock_to_save(save.id, code)
            
            loaded = service.load_save(save.id)
            for code in stock_codes:
                assert code in loaded.stock_codes, \
                    f"股票代码 {code} 应在存档中"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(
        name=valid_save_name(),
        stock_code=st.sampled_from(["600519", "000001", "300750"])
    )
    def test_duplicate_stock_not_added_twice(self, name: str, stock_code: str):
        """
        验证重复添加股票不会重复。
        
        *For any* 存档和股票代码：
        重复添加同一股票代码不应产生重复
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            save = service.create_save(name)
            
            # 添加两次
            service.add_stock_to_save(save.id, stock_code)
            service.add_stock_to_save(save.id, stock_code)
            
            loaded = service.load_save(save.id)
            count = loaded.stock_codes.count(stock_code)
            assert count == 1, f"股票代码 {stock_code} 应只出现一次，实际 {count} 次"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSaveDataCompleteness:
    """
    Property 8: Save Data Completeness
    Feature: save-system, Property 8: Save Data Completeness
    **Validates: Requirements 3.4, 3.5**
    
    *For any* save file, it SHALL contain all required fields: version, id, name, 
    config, account, gameState, stockCodes, tradeHistory, assetHistory.
    """
    
    @settings(max_examples=100)
    @given(name=valid_save_name(), initial_cash=valid_initial_cash())
    def test_save_file_has_all_required_fields(self, name: str, initial_cash: float):
        """
        验证存档文件包含所有必需字段。
        
        *For any* 存档文件：
        应包含所有必需字段
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            save = service.create_save(name, initial_cash)
            
            # 直接读取文件验证
            save_path = service._get_save_path(save.id)
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for field in REQUIRED_FIELDS:
                assert field in data, f"存档文件应包含字段: {field}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @settings(max_examples=100)
    @given(name=valid_save_name())
    def test_loaded_save_has_all_fields(self, name: str):
        """
        验证加载的存档对象包含所有字段。
        
        *For any* 加载的存档：
        SaveData 对象应有所有必需属性
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            service.create_save(name)
            loaded = service.load_save(service.sanitize_filename(name))
            
            assert loaded.version is not None, "version 不应为 None"
            assert loaded.id is not None, "id 不应为 None"
            assert loaded.name is not None, "name 不应为 None"
            assert loaded.config is not None, "config 不应为 None"
            assert loaded.account is not None, "account 不应为 None"
            assert loaded.game_state is not None, "game_state 不应为 None"
            assert loaded.stock_codes is not None, "stock_codes 不应为 None"
            assert loaded.trade_history is not None, "trade_history 不应为 None"
            assert loaded.asset_history is not None, "asset_history 不应为 None"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestInvalidSaveRejection:
    """
    Property 9: Invalid Save Rejection
    Feature: save-system, Property 9: Invalid Save Rejection
    **Validates: Requirements 4.5, 7.4**
    
    *For any* corrupted or invalid JSON file, or file missing required fields, 
    loading SHALL fail with an appropriate error rather than returning partial data.
    """
    
    def test_corrupted_json_rejected(self):
        """
        验证损坏的 JSON 文件被拒绝。
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建损坏的文件
            save_path = service.saves_dir / "corrupted.json"
            with open(save_path, "w") as f:
                f.write("{ invalid json }")
            
            with pytest.raises(SaveValidationError):
                service.load_save("corrupted")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_missing_required_field_rejected(self):
        """
        验证缺少必需字段的文件被拒绝。
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建缺少字段的文件
            save_path = service.saves_dir / "incomplete.json"
            with open(save_path, "w") as f:
                json.dump({"version": "1.0", "id": "incomplete"}, f)
            
            with pytest.raises(SaveValidationError):
                service.load_save("incomplete")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_invalid_account_structure_rejected(self):
        """
        验证无效的 account 结构被拒绝。
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            # 创建无效结构的文件
            save_path = service.saves_dir / "invalid_account.json"
            invalid_data = {
                "version": "1.0",
                "id": "invalid_account",
                "name": "test",
                "config": {},
                "account": "not_a_dict",  # 应该是字典
                "game_state": {},
                "stock_codes": [],
                "trade_history": [],
                "asset_history": []
            }
            with open(save_path, "w") as f:
                json.dump(invalid_data, f)
            
            with pytest.raises(SaveValidationError):
                service.load_save("invalid_account")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_nonexistent_save_rejected(self):
        """
        验证不存在的存档被拒绝。
        """
        temp_dir = tempfile.mkdtemp()
        service = SaveService(storage_dir=temp_dir)
        
        try:
            with pytest.raises(SaveNotFoundError):
                service.load_save("nonexistent")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
