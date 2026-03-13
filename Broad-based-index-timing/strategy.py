"""
宽基ETF轮动策略模块

核心逻辑：
1. 效率动量评分 = 动量 × 效率系数
2. 每天选择评分最高的Top2 ETF
3. 每只ETF分配50%仓位（共100%，满仓）
4. 使用前一日评分避免look ahead bias

动量公式：100 × ln(价格中枢20日前 / 价格中枢当前)
价格中枢 = (开盘价 + 最高价 + 最低价 + 收盘价) / 4

效率系数 = 方向性 / 波动性
- 方向性：净涨跌的绝对值
- 波动性：每日对数收益率绝对值之和
"""

import pandas as pd
import numpy as np
from typing import Dict


def calculate_efficiency_momentum(ohlc: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    计算效率动量评分

    使用价格中枢和对数收益率：
    - 动量 = 100 × ln(价格中枢20日前 / 价格中枢当前)
    - 效率系数 = 方向性 / 波动性
    - 评分 = 动量 × 效率系数

    Parameters:
    -----------
    ohlc : pd.DataFrame
        包含 open, high, low, close 列的DataFrame
    window : int
        动量窗口期，默认20

    Returns:
    --------
    pd.Series
        效率动量评分
    """
    # 计算价格中枢 = (O + H + L + C) / 4
    price_center = (ohlc['open'] + ohlc['high'] + ohlc['low'] + ohlc['close']) / 4

    # 1. 动量 = 100 × ln(价格中枢20日前 / 价格中枢当前)
    # 使用shift(window)获取window天前的价格，避免使用未来数据
    momentum = np.log(price_center / price_center.shift(window)) * 100

    # 2. 效率系数 = 方向性 / 波动性
    # 方向性：窗口期内的净涨跌（绝对值）
    direction = np.abs(price_center - price_center.shift(window))

    # 波动性：每日对数收益率绝对值之和
    daily_log_return = np.log(price_center / price_center.shift(1))
    volatility = pd.Series(np.abs(daily_log_return), index=price_center.index).rolling(window=window, min_periods=window).sum()

    # 避免除零
    epsilon = 1e-6
    efficiency = direction / (volatility + epsilon)

    # 3. 评分 = 动量 × 效率系数
    score = momentum * efficiency

    # 确保返回pandas Series
    return pd.Series(score, index=price_center.index)


def calculate_rotation_positions(all_assets_data: Dict[str, pd.DataFrame],
                                momentum_window: int = 20,
                                top_n: int = 2) -> pd.DataFrame:
    """
    计算轮动策略的每日仓位

    逻辑：
    1. 每天计算所有ETF的效率动量评分（使用OHLC数据）
    2. 选择评分最高的Top N个ETF
    3. 等资金分配仓位
    4. 使用前一日评分避免look ahead bias

    Parameters:
    -----------
    all_assets_data : dict
        所有ETF的价格数据字典（需包含OHLC数据）
    momentum_window : int
        动量窗口期
    top_n : int
        选择的头部标的数量

    Returns:
    --------
    pd.DataFrame
        各ETF的每日仓位
    """
    # 1. 获取所有日期范围（并集，从最早上市的ETF开始）
    all_dates_set = set()
    for df in all_assets_data.values():
        all_dates_set.update(df.index)
    common_dates = sorted(all_dates_set)

    print(f"日期范围: {common_dates[0]} ~ {common_dates[-1]} ({len(common_dates)}天)")

    # 2. 计算每个ETF的效率动量评分（每个ETF用自己的数据）
    scores_dict = {}
    for code, df in all_assets_data.items():
        # 每个ETF只用自己的数据计算评分
        scores_dict[code] = calculate_efficiency_momentum(df, window=momentum_window)

    # 3. 每日选择Top N（使用前一日评分避免look ahead bias）
    total_position = 1.0  # 总仓位100%（满仓）
    position_per_asset = total_position / top_n  # 每只ETF 50%

    positions = pd.DataFrame(0.0, index=common_dates, columns=list(scores_dict.keys()))

    # 跳过前面momentum_window天（因为评分需要窗口期数据）
    start_idx = momentum_window

    for i in range(start_idx, len(common_dates)):
        date = common_dates[i]
        prev_date = common_dates[i - 1]

        # 获取前一日评分
        prev_scores = pd.Series({code: scores_dict[code].loc[prev_date]
                                for code in scores_dict
                                if prev_date in scores_dict[code].index})

        # 过滤掉NaN评分
        prev_scores = prev_scores.dropna()

        if len(prev_scores) == 0:
            continue

        # 选择评分最高的Top N
        top_assets = prev_scores.nlargest(top_n).index.tolist()

        # 分配仓位
        for asset in top_assets:
            positions.loc[date, asset] = position_per_asset

    # 5. 非调仓日保持仓位（简单的仓位保持）
    positions = positions.reindex(common_dates)
    positions = positions.ffill().fillna(0.0)

    return positions


def generate_rotation_signals(all_assets_data: Dict[str, pd.DataFrame],
                            momentum_window: int = 20,
                            top_n: int = 2) -> Dict[str, pd.DataFrame]:
    """
    生成轮动信号（兼容旧接口）

    Parameters:
    -----------
    all_assets_data : dict
        所有ETF的价格数据
    momentum_window : int
        动量窗口期
    top_n : int
        选择的头部标的数量

    Returns:
    --------
    dict
        包含 positions 的字典
    """
    positions = calculate_rotation_positions(
        all_assets_data,
        momentum_window=momentum_window,
        top_n=top_n
    )

    return {
        'positions': positions
    }


# 保留必要的导入以兼容
__all__ = [
    'calculate_efficiency_momentum',
    'calculate_rotation_positions',
    'generate_rotation_signals'
]
