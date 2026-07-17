"""指标文件的保存、校验与计算。"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ALLOWED_METRICS = {"momentum", "ma_gap", "volume_ratio", "volatility", "rsi"}
ALLOWED_PYTHON_MODULES = {"math", "numpy", "pandas"}
FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
DEFAULT_INDICATOR_ID = "leek-resonance-index"
PYTHON_TIMEOUT_SECONDS = 5

DEFAULT_PYTHON_TEMPLATE = '''import pandas as pd


def calculate(data: pd.DataFrame) -> pd.Series:
    """返回与 data 等长的指标数值；数据不足的位置返回 NaN。"""
    close = data["close"].astype(float)
    fast_ma = close.rolling(5).mean()
    slow_ma = close.rolling(20).mean()
    return (fast_ma / slow_ma - 1) * 100
'''

LEEK_RESONANCE_CODE = '''import math
import numpy as np
import pandas as pd


def calculate(data: pd.DataFrame) -> pd.Series:
    """Leek共振指数 LRI：返回 0-100 的振荡值。"""
    close = data["close"].astype(float)
    volume = data["volume"].astype(float)
    returns = close.pct_change() * 100

    fast = returns.ewm(span=3, adjust=False).mean()
    slow = returns.ewm(span=8, adjust=False).mean()
    momentum = 0.7 * fast + 0.3 * slow

    volume_base = volume.shift(1).rolling(5, min_periods=1).mean()
    volume_term = np.log1p(volume / volume_base).replace([np.inf, -np.inf], np.nan).fillna(0)
    day_index = np.arange(1, len(data) + 1)
    mystic = 1 + 0.08 * np.sin(2 * math.pi * day_index / 8)

    raw = momentum * (1 + 0.5 * volume_term) * mystic
    result = 100 / (1 + np.exp(-raw.clip(-50, 50)))
    result.iloc[0] = np.nan
    return result
'''


class IndicatorError(Exception):
    pass


class IndicatorNotFoundError(IndicatorError):
    pass


class IndicatorValidationError(IndicatorError):
    pass


class IndicatorExecutionError(IndicatorError):
    pass


class IndicatorService:
    """管理可移植的 ``.indicator.json`` 指标文件。"""

    def __init__(self, storage_dir: str = "./storage/indicators"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_indicator()

    @staticmethod
    def _clean_id(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", value)
        if not cleaned:
            raise IndicatorValidationError("指标 ID 无效")
        return cleaned

    def _path(self, indicator_id: str) -> Path:
        return self.storage_dir / f"{self._clean_id(indicator_id)}.indicator.json"

    @staticmethod
    def _validate_python_code(code: str) -> None:
        if not code.strip():
            raise IndicatorValidationError("Python 指标代码不能为空")
        if len(code) > 30_000:
            raise IndicatorValidationError("Python 指标代码不能超过 30000 个字符")
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise IndicatorValidationError(
                f"Python 语法错误，第 {exc.lineno} 行：{exc.msg}"
            ) from exc

        has_calculate = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = (
                    [alias.name.split(".")[0] for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [(node.module or "").split(".")[0]]
                )
                if any(module not in ALLOWED_PYTHON_MODULES for module in modules):
                    raise IndicatorValidationError(
                        "仅允许导入 pandas、numpy 和 math"
                    )
            if isinstance(node, ast.FunctionDef) and node.name == "calculate":
                has_calculate = True
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_CALLS:
                raise IndicatorValidationError(f"不允许使用 {node.id}")
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                raise IndicatorValidationError("不允许访问双下划线属性")
        if not has_calculate:
            raise IndicatorValidationError("必须定义 calculate(data) 函数")

    def validate(self, definition: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(definition, dict):
            raise IndicatorValidationError("指标文件必须是 JSON 对象")

        name = str(definition.get("name", "")).strip()
        if not name or len(name) > 60:
            raise IndicatorValidationError("指标名称必填，且不能超过 60 个字符")

        language = str(definition.get("language") or (
            "python" if definition.get("code") else "builder"
        )).lower()
        if language not in {"python", "builder"}:
            raise IndicatorValidationError("指标语言必须是 python 或 builder")

        components = []
        code = ""
        if language == "python":
            code = str(definition.get("code", ""))
            self._validate_python_code(code)
        else:
            raw_components = definition.get("components")
            if not isinstance(raw_components, list) or not 1 <= len(raw_components) <= 8:
                raise IndicatorValidationError("搭建式指标必须包含 1 到 8 个计算分量")
            for index, item in enumerate(raw_components, start=1):
                if not isinstance(item, dict):
                    raise IndicatorValidationError(f"第 {index} 个分量格式错误")
                metric = str(item.get("metric", ""))
                if metric not in ALLOWED_METRICS:
                    raise IndicatorValidationError(f"不支持的指标分量：{metric}")
                try:
                    window = int(item.get("window", 0))
                    weight = float(item.get("weight", 0))
                except (TypeError, ValueError):
                    raise IndicatorValidationError(f"第 {index} 个分量的周期或权重无效")
                if not 2 <= window <= 250:
                    raise IndicatorValidationError("计算周期必须在 2 到 250 个交易日之间")
                if not -20 <= weight <= 20:
                    raise IndicatorValidationError("分量权重必须在 -20 到 20 之间")
                components.append({"metric": metric, "window": window, "weight": weight})

        try:
            buy_threshold = float(definition.get("buy_threshold", 1))
            sell_threshold = float(definition.get("sell_threshold", -1))
        except (TypeError, ValueError):
            raise IndicatorValidationError("买入或卖出阈值无效")
        if sell_threshold >= buy_threshold:
            raise IndicatorValidationError("卖出阈值必须小于买入阈值")

        indicator_id = definition.get("id") or uuid.uuid4().hex[:12]
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        return {
            "schema": "realstock-indicator/v2",
            "id": self._clean_id(str(indicator_id)),
            "name": name,
            "description": str(definition.get("description", "")).strip()[:500],
            "version": max(1, int(definition.get("version", 1))),
            "language": language,
            "code": code,
            "components": components,
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
            "builtin": bool(definition.get("builtin", False)),
            "created_at": str(definition.get("created_at") or now),
            "updated_at": now,
        }

    def _ensure_default_indicator(self) -> None:
        path = self._path(DEFAULT_INDICATOR_ID)
        created_at = None
        if path.exists():
            try:
                created_at = json.loads(path.read_text(encoding="utf-8")).get("created_at")
            except (OSError, json.JSONDecodeError, AttributeError):
                pass
        definition = self.validate({
            "id": DEFAULT_INDICATOR_ID,
            "name": "Leek共振指数",
            "description": "内置示例：动量、成交量和八日周期组合成 0-100 的 Leek共振指数。",
            "version": 1,
            "language": "python",
            "code": LEEK_RESONANCE_CODE,
            "buy_threshold": 88,
            "sell_threshold": 44,
            "builtin": True,
            "created_at": created_at,
        })
        path.write_text(
            json.dumps(definition, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list(self) -> list[dict[str, Any]]:
        definitions = []
        for path in self.storage_dir.glob("*.indicator.json"):
            try:
                definitions.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return sorted(
            definitions,
            key=lambda item: (not item.get("builtin", False), item.get("updated_at", "")),
        )

    def get(self, indicator_id: str) -> dict[str, Any]:
        path = self._path(indicator_id)
        if not path.exists():
            raise IndicatorNotFoundError("指标不存在")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IndicatorValidationError("指标文件已损坏") from exc

    def save(self, definition: dict[str, Any]) -> dict[str, Any]:
        normalized = self.validate(definition)
        path = self._path(normalized["id"])
        if normalized["id"] == DEFAULT_INDICATOR_ID and path.exists():
            raise IndicatorValidationError("内置指标不能覆盖，请另存为新指标")
        if path.exists():
            previous = self.get(normalized["id"])
            normalized["created_at"] = previous.get("created_at", normalized["created_at"])
        normalized["builtin"] = False
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temp_path.replace(path)
        return normalized

    def delete(self, indicator_id: str) -> bool:
        if indicator_id == DEFAULT_INDICATOR_ID:
            raise IndicatorValidationError("内置指标不能删除")
        path = self._path(indicator_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    @staticmethod
    def _signals(
        values: list[float | None], buy_threshold: float, sell_threshold: float
    ) -> list[str]:
        return [
            "warming_up" if value is None
            else "buy" if value >= buy_threshold
            else "sell" if value <= sell_threshold
            else "hold"
            for value in values
        ]

    def _compute_python_values(
        self, definition: dict[str, Any], frame: pd.DataFrame
    ) -> list[float | None]:
        runner_path = Path(__file__).with_name("indicator_runner.py")
        with tempfile.TemporaryDirectory(prefix="realstock-indicator-") as temp_dir:
            temp = Path(temp_dir)
            code_path = temp / "indicator.py"
            input_path = temp / "input.csv"
            output_path = temp / "output.json"
            code_path.write_text(definition["code"], encoding="utf-8")
            frame.to_csv(input_path, index=False)
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            try:
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        str(runner_path),
                        str(code_path),
                        str(input_path),
                        str(output_path),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=PYTHON_TIMEOUT_SECONDS,
                    creationflags=creation_flags,
                    env={**os.environ, "PYTHONNOUSERSITE": "1"},
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise IndicatorExecutionError(
                    f"指标计算超过 {PYTHON_TIMEOUT_SECONDS} 秒，已终止"
                ) from exc
            if completed.returncode != 0 or not output_path.exists():
                error = (completed.stderr or completed.stdout or "指标执行失败").strip()
                raise IndicatorExecutionError(error[-800:])
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            return payload["values"]

    @staticmethod
    def _compute_builder_values(
        definition: dict[str, Any], frame: pd.DataFrame
    ) -> tuple[list[float | None], dict[str, pd.Series]]:
        data = frame.sort_values("date").reset_index(drop=True).copy()
        close = pd.to_numeric(data["close"], errors="coerce")
        volume = pd.to_numeric(data["volume"], errors="coerce")
        score = pd.Series(0.0, index=data.index)
        valid = pd.Series(True, index=data.index)
        component_series: dict[str, pd.Series] = {}

        for index, component in enumerate(definition["components"]):
            metric = component["metric"]
            window = component["window"]
            key = f"{metric}_{window}_{index + 1}"
            if metric == "momentum":
                values = close.pct_change(window) * 100
            elif metric == "ma_gap":
                values = (close / close.rolling(window).mean() - 1) * 100
            elif metric == "volume_ratio":
                values = (volume / volume.rolling(window).mean() - 1) * 100
            elif metric == "volatility":
                values = close.pct_change().rolling(window).std() * np.sqrt(window) * 100
            else:
                delta = close.diff()
                gains = delta.clip(lower=0).rolling(window).mean()
                losses = (-delta.clip(upper=0)).rolling(window).mean()
                relative_strength = gains / losses
                values = (100 - (100 / (1 + relative_strength))) - 50
                values = values.mask((losses == 0) & (gains > 0), 50)
                values = values.mask((losses == 0) & (gains == 0), 0)
            component_series[key] = values
            valid &= values.notna()
            score = score + values.fillna(0) * component["weight"]

        output = [
            round(float(score.iloc[index]), 6) if valid.iloc[index] else None
            for index in data.index
        ]
        return output, component_series

    def compute(self, definition: dict[str, Any], frame: pd.DataFrame) -> list[dict[str, Any]]:
        normalized = self.validate(definition)
        if frame.empty:
            return []
        data = frame.sort_values("date").reset_index(drop=True).copy()
        components: dict[str, pd.Series] = {}
        if normalized["language"] == "python":
            values = self._compute_python_values(normalized, data)
        else:
            values, components = self._compute_builder_values(normalized, data)
        signals = self._signals(
            values, normalized["buy_threshold"], normalized["sell_threshold"]
        )

        return [
            {
                "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                "value": round(float(values[index]), 6) if values[index] is not None else None,
                "signal": signals[index],
                "components": {
                    key: (
                        round(float(series.iloc[index]), 6)
                        if pd.notna(series.iloc[index]) else None
                    )
                    for key, series in components.items()
                },
            }
            for index, (_, row) in enumerate(data.iterrows())
        ]
