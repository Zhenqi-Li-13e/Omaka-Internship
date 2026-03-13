"""
回测系统模块
执行策略回测、仓位计算、收益计算
交易成本规则：
- A股ETF单边：手续费0.01% + 滑点0.02% = 0.03%
- 跨境ETF单边：手续费0.02% + 滑点0.02% = 0.04%
- 买入/卖出各扣一次
"""

import os
import pandas as pd
import numpy as np
from typing import Dict
from strategy import generate_rotation_signals
# from risk_control import DrawdownController  # 回撤控制已禁用

# 交易成本配置
# A股ETF：手续费0.01% + 滑点0.02% = 0.03%
# 跨境ETF：手续费0.02% + 滑点0.02% = 0.04%
COST_A_SHARE = 0.0003  # A股ETF单边成本
COST_CROSS_BORDER = 0.0004  # 跨境ETF单边成本


def get_etf_cost(etf_code: str, etf_info: dict | None = None) -> float:
    """获取单只ETF的单边交易成本"""
    if etf_info and etf_code in etf_info:
        etf_type = etf_info[etf_code].get('type', 'A')
        if etf_type == 'CROSS':
            return COST_CROSS_BORDER
    # 默认认为是A股ETF
    return COST_A_SHARE


def backtest_rotation_strategy(all_assets_data: Dict[str, pd.DataFrame],
                              momentum_window: int = 20,
                              top_n: int = 2,
                              initial_capital: float = 1000000.0,
                              etf_info: Dict[str, dict] | None = None) -> dict:
    """
    轮动策略回测

    成本规则：
    - A股ETF单边：手续费0.01% + 滑点0.02% = 0.03%
    - 跨境ETF单边：手续费0.02% + 滑点0.02% = 0.04%
    - 买入/卖出各扣一次

    Parameters:
    -----------
    all_assets_data : dict
        ETF价格数据
    momentum_window : int
        动量窗口期
    top_n : int
        选择的头部标的数量
    initial_capital : float
        初始资金
    etf_info : dict
        ETF信息字典，用于区分A股和跨境ETF
    """
    print("\n" + "=" * 60)
    print("开始轮动策略回测")
    print("=" * 60)

    # 1. 生成轮动信号
    print("\n[1/3] 生成轮动信号...")
    rotation_signals = generate_rotation_signals(
        all_assets_data,
        momentum_window=momentum_window,
        top_n=top_n
    )

    positions_df = rotation_signals['positions']
    dates = positions_df.index
    etf_codes = positions_df.columns

    print(f"  仓位数据: {len(positions_df)} 个交易日")

    # 2. 计算每日净值（不含回撤控制）
    print("\n[2/3] 计算每日净值...")

    # 回撤控制已禁用
    # dd_controller = DrawdownController()

    nav_series = pd.Series(initial_capital, index=dates, dtype=float)
    daily_returns = []

    # 保存前一天的调整后仓位
    prev_adjusted_positions = None

    for i in range(1, len(dates)):
        date = dates[i]
        prev_date = dates[i-1]

        # ====== 仓位（无回撤控制）======
        day_positions = positions_df.loc[date]
        adjusted_day_positions = day_positions  # 直接使用原始仓位

        # ====== 收益计算 ======
        # 用前一日调整后的仓位来计算收益
        if prev_adjusted_positions is None:
            prev_adjusted_positions = positions_df.loc[prev_date]

        # 计算当日组合收益
        gross_return = 0.0
        transaction_cost = 0.0

        for etf_code in etf_codes:
            position = adjusted_day_positions[etf_code]
            prev_position = prev_adjusted_positions[etf_code]

            if position > 0 or prev_position > 0:
                prices = all_assets_data[etf_code]['close']

                if date in prices.index and prev_date in prices.index:
                    price_today = prices.loc[date]
                    price_yesterday = prices.loc[prev_date]

                    if price_yesterday > 0:
                        asset_return = price_today / price_yesterday - 1
                        # 使用前一日仓位计算收益
                        gross_return += prev_position * asset_return

                        # 交易成本计算：买入和卖出各扣一次
                        # 仓位变化 = |当日仓位 - 前日仓位|
                        position_change = abs(position - prev_position)
                        if position_change > 0:
                            # 获取该ETF的单边成本
                            cost_rate = get_etf_cost(etf_code, etf_info)
                            # 买入和卖出各扣一次，所以乘以2
                            transaction_cost += position_change * cost_rate * 2

        # 净收益
        net_return = gross_return - transaction_cost
        nav_series.loc[date] = nav_series.loc[prev_date] * (1 + net_return)

        # 记录当日调整后的实际仓位
        daily_returns.append({
            'date': date,
            'position': adjusted_day_positions.sum(),
            'gross_return': gross_return,
            'transaction_cost': transaction_cost,
            'net_return': net_return
        })

        # 保存当日仓位供明日使用
        prev_adjusted_positions = adjusted_day_positions.copy()

    returns_df = pd.DataFrame(daily_returns).set_index('date')

    # 3. 计算基准
    print("\n[3/3] 计算基准...")
    hs300_code = '000300'
    if hs300_code in all_assets_data:
        # 只用沪深300有数据的日期（与dates交集）
        hs300_dates = [d for d in dates if d in all_assets_data[hs300_code]['close'].index]
        hs300_prices = all_assets_data[hs300_code]['close'].loc[hs300_dates]
        hs300_nav = (1 + hs300_prices.pct_change().fillna(0)).cumprod() * initial_capital
    else:
        hs300_nav = pd.Series(initial_capital, index=dates)

    # 等权组合基准
    equal_weight_nav = pd.Series(initial_capital, index=dates, dtype=float)
    for i in range(1, len(dates)):
        date = dates[i]
        prev_date = dates[i-1]

        daily_return = 0.0
        for etf_code in etf_codes:
            prices = all_assets_data[etf_code]['close']
            if date in prices.index and prev_date in prices.index:
                daily_return += prices.loc[date] / prices.loc[prev_date] - 1

        daily_return /= len(etf_codes)
        equal_weight_nav.loc[date] = equal_weight_nav.loc[prev_date] * (1 + daily_return)

    # 4. 整合结果
    results = {
        'positions': positions_df,
        'nav': nav_series,
        'returns': returns_df,
        'buy_and_hold': hs300_nav,
        'equal_weight_nav': equal_weight_nav,
        'params': {
            'momentum_window': momentum_window,
            'top_n': top_n
        },
        'initial_capital': initial_capital,
        'etf_codes': list(etf_codes),
        'all_assets_data': all_assets_data
    }

    # 计算年化收益
    years = len(dates) / 252

    # 轮动策略
    strategy_total_return = nav_series.iloc[-1] / initial_capital - 1
    strategy_annual_return = (1 + strategy_total_return) ** (1 / years) - 1

    # 沪深300基准
    benchmark_total_return = hs300_nav.iloc[-1] / initial_capital - 1
    benchmark_annual_return = (1 + benchmark_total_return) ** (1 / years) - 1

    # 等权组合基准
    equal_weight_total_return = equal_weight_nav.iloc[-1] / initial_capital - 1
    equal_weight_annual_return = (1 + equal_weight_total_return) ** (1 / years) - 1

    # 超额收益（两种口径）
    excess_total_vs_hs300 = strategy_total_return - benchmark_total_return
    excess_annual_vs_hs300 = strategy_annual_return - benchmark_annual_return
    excess_total_vs_equal = strategy_total_return - equal_weight_total_return
    excess_annual_vs_equal = strategy_annual_return - equal_weight_annual_return

    # 绩效总结CSV
    perf_data = {
        '指标': [
            '轮动策略_区间累计总收益', '轮动策略_年化收益率',
            '沪深300_区间累计总收益', '沪深300_年化收益率',
            '等权组合_区间累计总收益', '等权组合_年化收益率',
            '超额收益(vs沪深300)_总收益差值', '超额收益(vs沪深300)_年化收益差值',
            '超额收益(vs等权组合)_总收益差值', '超额收益(vs等权组合)_年化收益差值'
        ],
        '数值': [
            strategy_total_return, strategy_annual_return,
            benchmark_total_return, benchmark_annual_return,
            equal_weight_total_return, equal_weight_annual_return,
            excess_total_vs_hs300, excess_annual_vs_hs300,
            excess_total_vs_equal, excess_annual_vs_equal
        ]
    }
    return results


# 兼容旧接口
__all__ = ['backtest_rotation_strategy']
