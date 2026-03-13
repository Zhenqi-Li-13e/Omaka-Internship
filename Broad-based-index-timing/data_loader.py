"""
数据获取模块
使用AkShare获取A股宽基指数、ETF及美股数据
支持10个ETF的多资产轮动策略
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict


# ETF/指数代码配置
ETF_INFO = {
    "000016": {"name": "上证50", "type": "index"},
    "000300": {"name": "沪深300", "type": "index"},
    "000905": {"name": "中证500", "type": "index"},
    "000852": {"name": "中证1000", "type": "index"},
    "399006": {"name": "创业板", "type": "index"},
    "000688": {"name": "科创50", "type": "index"},
    "NDX": {"name": "纳指100", "type": "us_stock"},
    "SPX": {"name": "标普500", "type": "us_stock"},
    "518880": {"name": "黄金ETF", "type": "etf"},
    "000015": {"name": "红利低波", "type": "index"},
}


def get_index_data(index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取单个A股指数的历史日线数据

    Parameters:
    -----------
    index_code : str
        指数代码，例如 '000300' (沪深300), '000905' (中证500)
    start_date : str
        开始日期，格式 'YYYY-MM-DD'
    end_date : str
        结束日期，格式 'YYYY-MM-DD'

    Returns:
    --------
    pd.DataFrame
        包含日期、开盘、最高、最低、收盘、成交量等字段
    """
    try:
        # 转换日期格式为 YYYYMMDD
        start_str = start_date.replace("-", "")
        end_str = end_date.replace("-", "")

        # 使用 AkShare 的 index_zh_a_hist 接口
        df = ak.index_zh_a_hist(
            symbol=index_code, period="daily", start_date=start_str, end_date=end_str
        )

        # AkShare 返回的列名是中文，需要转换
        df = df.rename(
            columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
            }
        )

        # 转换日期格式
        df["date"] = pd.to_datetime(df["date"])

        # 设置日期索引
        df = df.set_index("date")

        # 按日期排序
        df = df.sort_index()

        return df

    except Exception as e:
        print(f"获取指数 {index_code} 数据失败: {e}")
        return pd.DataFrame()


def get_us_stock_data(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取美股历史数据（支持指数和个股）

    Parameters:
    -----------
    stock_code : str
        美股代码，例如 'NDX' (纳指100), 'SPX' (标普500), 'IXIC' (纳斯达克综合)
        或个股代码如 'AAPL', 'MSFT'
    start_date : str
        开始日期，格式 'YYYY-MM-DD'
    end_date : str
        结束日期，格式 'YYYY-MM-DD'

    Returns:
    --------
    pd.DataFrame
        包含日期、开盘、最高、最低、收盘、成交量等字段
    """
    try:
        # 日期过滤使用原始格式

        # 美股指数代码到新浪symbol的映射
        index_symbol_map = {
            "NDX": ".NDX",    # 纳斯达克100
            "SPX": ".INX",    # 标普500
            "IXIC": ".IXIC",  # 纳斯达克综合
        }

        # 判断是否为美股指数
        if stock_code in index_symbol_map:
            # 使用 index_us_stock_sina 接口获取指数数据
            symbol = index_symbol_map[stock_code]
            df = ak.index_us_stock_sina(symbol=symbol)

            if df is None or df.empty:
                print(f"获取美股指数 {stock_code} 数据为空")
                return pd.DataFrame()

            # 列名已是英文：date, open, high, low, close, volume
            # 确保volume字段存在，若无则补充
            if "volume" not in df.columns:
                df["volume"] = 0

        else:
            # 使用 stock_us_hist 接口获取个股数据
            df = ak.stock_us_hist(symbol=stock_code, period="daily")

            if df is None or df.empty:
                print(f"获取美股 {stock_code} 数据为空")
                return pd.DataFrame()

            # 重命名列
            df = df.rename(
                columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                }
            )

        # 统一将date列转换为pd.Timestamp类型
        df["date"] = pd.to_datetime(df["date"])

        # 按日期过滤数据
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]

        # 设置日期索引
        df = df.set_index("date")

        # 按日期排序
        df = df.sort_index()

        return df

    except Exception as e:
        print(f"获取美股 {stock_code} 数据失败: {e}")
        return pd.DataFrame()


def get_etf_data(etf_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    获取ETF或指数数据（根据代码类型自动选择数据源）

    Parameters:
    -----------
    etf_code : str
        ETF或指数代码
    start_date : str
        开始日期，格式 'YYYY-MM-DD'
    end_date : str
        结束日期，格式 'YYYY-MM-DD'

    Returns:
    --------
    pd.DataFrame
        包含日期、开盘、最高、最低、收盘、成交量等字段
    """
    # 检查是否为美股
    if etf_code in ["NDX", "SPX"]:
        return get_us_stock_data(etf_code, start_date, end_date)
    else:
        # A股指数或ETF
        return get_index_data(etf_code, start_date, end_date)


def get_all_etf_data(
    start_date: str = "2014-01-01",
    end_date: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    获取所有10个ETF的历史数据

    Parameters:
    -----------
    start_date : str
        开始日期
    end_date : str, optional
        结束日期，默认为当前日期
    use_cache : bool
        是否使用缓存数据

    Returns:
    --------
    dict
        字典，key为ETF代码，value为对应的DataFrame
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    data = {}

    print("=" * 60)
    print("开始下载10个ETF/指数数据...")
    print("=" * 60)

    for code, info in ETF_INFO.items():
        name = info["name"]
        print(f"\n正在下载 {name} ({code})...")

        # 尝试获取数据
        df = get_etf_data(code, start_date, end_date)

        if not df.empty:
            # 确保必要的列存在
            required_cols = ["open", "close", "high", "low", "volume"]
            if all(col in df.columns for col in required_cols):
                data[code] = df
                print(
                    f"  成功: {len(df)} 条记录, 时间范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}"
                )
            else:
                print(f"  数据列不完整，跳过")
        else:
            print(f"  获取失败")

    print(f"\n{'=' * 60}")
    print(f"数据下载完成，成功获取 {len(data)}/{len(ETF_INFO)} 个ETF数据")
    print(f"{'=' * 60}")

    return data


def align_etf_data(data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    对齐所有ETF数据

    处理逻辑：
    1. 不要求所有ETF同时存在，每个ETF从自己的上市日期开始参与
    2. A股和美股分别取各自的交易日交集，然后合并
    3. 不使用 ffill/bfill 填充，避免引入未来数据

    Parameters:
    -----------
    data : dict
        ETF数据字典

    Returns:
    --------
    dict
        对齐后的ETF数据字典
    """
    if not data:
        return data

    # 识别市场类型
    us_codes = {"NDX", "SPX"}

    # 分别获取A股和美股的交易日交集
    cn_dates_set = set()
    us_dates_set = set()

    for code, df in data.items():
        df_dates = set(df.index)
        if code in us_codes:
            if not us_dates_set:
                us_dates_set = df_dates
            else:
                us_dates_set = us_dates_set.intersection(df_dates)
        else:
            if not cn_dates_set:
                cn_dates_set = df_dates
            else:
                cn_dates_set = cn_dates_set.intersection(df_dates)

    # 合并A股和美股的交易日（取并集，这样每个ETF可以从自己的上市日开始）
    all_dates_set = cn_dates_set.union(us_dates_set)

    if not all_dates_set:
        print("警告: 没有共同的交易日")
        return data

    # 每个ETF保持自己的原始数据，不做截断
    # 这样科创50可以从2019-12-31开始，其他ETF从2014开始
    aligned_data = data.copy()

    print(f"数据对齐完成，每个ETF从其上市日期开始参与轮动")

    return aligned_data


def save_etf_data(data: Dict[str, pd.DataFrame], folder: str = "data") -> None:
    """
    保存ETF数据到本地CSV文件

    Parameters:
    -----------
    data : dict
        ETF数据字典
    folder : str
        保存文件夹
    """
    import os

    # 创建文件夹
    if not os.path.exists(folder):
        os.makedirs(folder)

    # 保存每个ETF的数据
    for code, df in data.items():
        filename = f"{folder}/{code}.csv"
        df.to_csv(filename)
        name = ETF_INFO.get(code, {}).get("name", code)
        print(f"已保存 {name} ({code}) 数据到 {filename}")


def load_etf_data(folder: str = "data") -> Dict[str, pd.DataFrame]:
    """
    从本地CSV文件加载ETF数据

    Parameters:
    -----------
    folder : str
        数据文件夹

    Returns:
    --------
    dict
        字典，key为ETF代码，value为对应的DataFrame
    """
    import os

    data = {}

    if not os.path.exists(folder):
        print(f"数据文件夹 {folder} 不存在")
        return data

    # 遍历文件夹中的CSV文件
    for filename in os.listdir(folder):
        if filename.endswith(".csv"):
            code = filename.replace(".csv", "")
            filepath = os.path.join(folder, filename)
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            data[code] = df

    print(f"已加载 {len(data)} 个ETF数据")

    return data


# 保留原有函数以兼容旧代码
def get_all_indices_data(
    start_date: str = "2010-01-01", end_date: Optional[str] = None
) -> dict:
    """
    获取所有宽基指数的历史数据（兼容旧代码）

    Parameters:
    -----------
    start_date : str
        开始日期
    end_date : str, optional
        结束日期，默认为当前日期

    Returns:
    --------
    dict
        字典，key为指数代码，value为对应的DataFrame
    """
    # 只保留原有的4个宽基指数
    indices = {
        "000300": "沪深300",
        "000905": "中证500",
        "000852": "中证1000",
        "000016": "上证50",
    }

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    data = {}

    print("开始下载指数数据...")
    for code, name in indices.items():
        print(f"  正在下载 {name} ({code})...")
        df = get_index_data(code, start_date, end_date)
        if not df.empty:
            data[code] = df
            print(f"    获取成功: {len(df)} 条记录")
        else:
            print(f"    获取失败")

    print(f"数据下载完成，共获取 {len(data)} 个指数数据")

    return data


def save_index_data(data: dict, folder: str = "data") -> None:
    """保存指数数据到本地CSV文件（兼容旧代码）"""
    save_etf_data(data, folder)


def load_index_data(folder: str = "data") -> dict:
    """从本地CSV文件加载指数数据（兼容旧代码）"""
    return load_etf_data(folder)


# 测试代码
if __name__ == "__main__":
    # 测试数据获取
    data = get_all_etf_data("2020-01-01", "2024-12-31")
    print("\n各ETF数据概览:")
    for code, df in data.items():
        name = ETF_INFO.get(code, {}).get("name", code)
        print(f"  {name}: {len(df)} 条记录")
