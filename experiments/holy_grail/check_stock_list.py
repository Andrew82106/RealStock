"""临时脚本：测试股票列表备选接口的连通性。"""
import akshare as ak

try:
    df = ak.stock_info_a_code_name()
    print("stock_info_a_code_name OK, rows:", len(df))
    print(df.head(3))
except Exception as e:
    print("stock_info_a_code_name failed:", str(e)[:150])

try:
    df = ak.stock_zh_a_spot_em()
    print("stock_zh_a_spot_em OK, rows:", len(df))
except Exception as e:
    print("stock_zh_a_spot_em failed:", str(e)[:150])
