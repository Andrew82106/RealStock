"""Python 指标子进程执行器。

此文件由 IndicatorService 通过隔离模式 Python 子进程调用，不直接作为 API 使用。
"""

from __future__ import annotations

import json
import math
import runpy
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    if len(sys.argv) != 4:
        raise RuntimeError("runner arguments invalid")
    code_path = Path(sys.argv[1])
    input_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    frame = pd.read_csv(input_path)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    namespace = runpy.run_path(str(code_path))
    calculate = namespace.get("calculate")
    if not callable(calculate):
        raise RuntimeError("必须定义 calculate(data) 函数")

    calculated = calculate(frame.copy())
    if isinstance(calculated, pd.DataFrame):
        if "value" not in calculated.columns:
            raise RuntimeError("DataFrame 返回值必须包含 value 列")
        calculated = calculated["value"]
    if not isinstance(calculated, pd.Series):
        calculated = pd.Series(calculated)
    if len(calculated) != len(frame):
        raise RuntimeError(
            f"返回长度必须与输入一致：输入 {len(frame)}，返回 {len(calculated)}"
        )

    numeric = pd.to_numeric(calculated.reset_index(drop=True), errors="raise")
    values = [
        float(value) if pd.notna(value) and math.isfinite(float(value)) else None
        for value in numeric
    ]
    output_path.write_text(
        json.dumps({"values": values}, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()

