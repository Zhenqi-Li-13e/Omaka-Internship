"""
绩效指标计算模块
计算年化收益率、波动率、Sharpe Ratio、最大回撤、Calmar Ratio、胜率、换手率
"""

import pandas as pd
import numpy as np
from typing import Optional, List


def calculate_annual_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    计算年化收益率

    Parameters:
    -----------
    returns : pd.Series
        日收益率序列
    periods_per_year : int
        每年交易日数量，默认252

    Returns:
    --------
    float
        年化收益率
    """
    # 计算投资年限
    years = len(returns) / periods_per_year

    if years > 0 and len(returns) > 0:
        # 总收益率 - 使用累乘
        total_return = 1.0
        for r in returns:
            total_return *= (1 + r)
        total_return -= 1

        # 使用对数计算年化收益率
        if 1 + total_return > 0:
            annual_return = np.exp(np.log(1 + total_return) / years) - 1
        else:
            annual_return = -np.exp(np.log(-(1 + total_return)) / years) - 1
    else:
        annual_return = 0.0

    return float(annual_return)


def calculate_annual_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    计算年化波动率

    Parameters:
    -----------
    returns : pd.Series
        日收益率序列
    periods_per_year : int
        每年交易日数量，默认252

    Returns:
    --------
    float
        年化波动率
    """
    return returns.std() * np.sqrt(periods_per_year)


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0,
                          periods_per_year: int = 252) -> float:
    """
    计算Sharpe Ratio

    Parameters:
    -----------
    returns : pd.Series
        日收益率序列
    risk_free_rate : float
        年化无风险利率
    periods_per_year : int
        每年交易日数量，默认252

    Returns:
    --------
    float
        Sharpe Ratio
    """
    # 年化收益率
    annual_return = calculate_annual_return(returns, periods_per_year)

    # 年化波动率
    annual_vol = calculate_annual_volatility(returns, periods_per_year)

    # Sharpe Ratio
    if annual_vol > 0:
        sharpe = (annual_return - risk_free_rate) / annual_vol
    else:
        sharpe = 0.0

    return sharpe


def calculate_max_drawdown(nav: pd.Series) -> float:
    """
    计算最大回撤

    Parameters:
    -----------
    nav : pd.Series
        净值序列

    Returns:
    --------
    float
        最大回撤 (负数)
    """
    # 计算历史高点
    peak = nav.expanding().max()

    # 计算回撤
    drawdown = (nav - peak) / peak

    # 返回最大回撤
    return drawdown.min()


def calculate_calmar_ratio(annual_return: float, max_drawdown: float) -> float:
    """
    计算Calmar Ratio

    Parameters:
    -----------
    annual_return : float
        年化收益率
    max_drawdown : float
        最大回撤 (负数)

    Returns:
    --------
    float
        Calmar Ratio
    """
    # 取绝对值
    dd_abs = abs(max_drawdown)

    if dd_abs > 0:
        calmar = annual_return / dd_abs
    else:
        calmar = 0.0

    return calmar


def calculate_win_rate(returns: pd.Series) -> float:
    """
    计算胜率

    Parameters:
    -----------
    returns : pd.Series
        日收益率序列

    Returns:
    --------
    float
        胜率 (0-1)
    """
    if len(returns) == 0:
        return 0.0

    winning_days = (returns > 0).sum()
    total_days = len(returns)

    return winning_days / total_days


def calculate_turnover(positions: pd.Series) -> float:
    """
    计算换手率

    Parameters:
    -----------
    positions : pd.Series
        仓位序列

    Returns:
    --------
    float
        平均换手率 (每年)
    """
    # 计算仓位变化
    position_changes = positions.diff().abs()

    # 计算总换手率
    total_turnover = position_changes.sum()

    # 转换为年均换手率
    years = len(positions) / 252

    if years > 0:
        annual_turnover = total_turnover / years
    else:
        annual_turnover = 0.0

    return annual_turnover


def calculate_avg_holding_period(positions: pd.Series) -> float:
    """
    计算平均持仓周期（天）

    Parameters:
    -----------
    positions : pd.Series
        仓位序列

    Returns:
    --------
    float
        平均持仓天数
    """
    # 找出持仓变化的点
    position_changes = positions.diff().abs() > 0

    if position_changes.sum() == 0:
        # 没有交易，返回整个回测周期
        return float(len(positions))

    # 计算相邻交易之间的天数
    change_indices = position_changes[position_changes].index.tolist()

    if len(change_indices) < 2:
        return float(len(positions))

    holding_periods = []
    for i in range(1, len(change_indices)):
        # 计算天数差
        if hasattr(change_indices[i], 'days'):
            days = (change_indices[i] - change_indices[i-1]).days
        else:
            # 如果是整数索引，假设每天一条数据
            days = 1
        holding_periods.append(days)

    return float(np.mean(holding_periods)) if holding_periods else float(len(positions))


def calculate_profit_factor(returns: pd.Series) -> float:
    """
    计算盈利因子 (Profit Factor)

    Parameters:
    -----------
    returns : pd.Series
        日收益率序列

    Returns:
    --------
    float
        盈利因子
    """
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = np.inf if gross_profit > 0 else 0.0

    return profit_factor


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0,
                           periods_per_year: int = 252) -> float:
    """
    计算Sortino Ratio (使用下行波动率)

    Parameters:
    -----------
    returns : pd.Series
        日收益率序列
    risk_free_rate : float
        年化无风险利率
    periods_per_year : int
        每年交易日数量

    Returns:
    --------
    float
        Sortino Ratio
    """
    # 年化收益率
    annual_return = calculate_annual_return(returns, periods_per_year)

    # 下行波动率 (只考虑负收益)
    negative_returns = returns[returns < 0]
    if len(negative_returns) > 0:
        downside_std = negative_returns.std() * np.sqrt(periods_per_year)
    else:
        downside_std = 0.0

    # Sortino Ratio
    if downside_std > 0:
        sortino = (annual_return - risk_free_rate) / downside_std
    else:
        sortino = 0.0

    return sortino


def calculate_all_metrics(returns: pd.Series, nav: pd.Series,
                          positions: pd.Series) -> dict:
    """
    计算所有绩效指标

    Parameters:
    -----------
    returns : pd.Series
        日收益率序列
    nav : pd.Series
        净值序列
    positions : pd.Series
        仓位序列

    Returns:
    --------
    dict
        绩效指标字典
    """
    # 基础指标
    annual_return = calculate_annual_return(returns)
    annual_volatility = calculate_annual_volatility(returns)
    max_drawdown = calculate_max_drawdown(nav)

    # 衍生指标
    sharpe_ratio = calculate_sharpe_ratio(returns)
    calmar_ratio = calculate_calmar_ratio(annual_return, max_drawdown)
    win_rate = calculate_win_rate(returns)
    turnover = calculate_turnover(positions)
    profit_factor = calculate_profit_factor(returns)
    sortino_ratio = calculate_sortino_ratio(returns)
    avg_holding_period = calculate_avg_holding_period(positions)

    # 总收益率
    total_return = (nav.iloc[-1] / nav.iloc[0] - 1) if len(nav) > 0 else 0.0

    metrics = {
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_volatility': annual_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'turnover': turnover,
        'avg_holding_period': avg_holding_period,
        'profit_factor': profit_factor,
        'num_trading_days': len(returns),
        'final_nav': nav.iloc[-1] if len(nav) > 0 else 0.0
    }

    return metrics


def format_metrics_table(metrics_list: list, index_names: Optional[List[str]] = None) -> pd.DataFrame:
    """
    格式化绩效指标表

    Parameters:
    -----------
    metrics_list : list
        绩效指标字典列表
    index_names : list, optional
        索引名称列表

    Returns:
    --------
    pd.DataFrame
        格式化的绩效指标表
    """
    # 创建DataFrame
    df = pd.DataFrame(metrics_list)

    # 设置索引
    if index_names is not None:
        df.index = index_names

    # 格式化数值
    format_dict = {
        'total_return': '{:.2%}',
        'annual_return': '{:.2%}',
        'annual_volatility': '{:.2%}',
        'sharpe_ratio': '{:.3f}',
        'sortino_ratio': '{:.3f}',
        'max_drawdown': '{:.2%}',
        'calmar_ratio': '{:.3f}',
        'win_rate': '{:.2%}',
        'turnover': '{:.2f}',
        'avg_holding_period': '{:.1f}',
        'profit_factor': '{:.3f}',
        'final_nav': '{:.2f}'
    }

    return df


def print_performance_report(results: dict, index_name: str = '') -> dict:
    """
    打印绩效报告

    Parameters:
    -----------
    results : dict
        回测结果字典
    index_name : str
        指数名称
    """
    # 提取数据
    returns = results['returns']['strategy_return']
    nav = results['nav']
    positions = results['positions']

    # 计算指标
    metrics = calculate_all_metrics(returns, nav, positions)

    # 打印报告
    print(f"\n{'='*60}")
    print(f"绩效报告 - {index_name}")
    print(f"{'='*60}")
    print(f"总收益率:      {metrics['total_return']:.2%}")
    print(f"年化收益率:    {metrics['annual_return']:.2%}")
    print(f"年化波动率:    {metrics['annual_volatility']:.2%}")
    print(f"Sharpe Ratio:  {metrics['sharpe_ratio']:.3f}")
    print(f"Sortino Ratio: {metrics['sortino_ratio']:.3f}")
    print(f"最大回撤:      {metrics['max_drawdown']:.2%}")
    print(f"Calmar Ratio:  {metrics['calmar_ratio']:.3f}")
    print(f"胜率:          {metrics['win_rate']:.2%}")
    print(f"年均换手率:    {metrics['turnover']:.2f}")
    print(f"平均持仓周期:  {metrics['avg_holding_period']:.1f} 天")
    print(f"盈利因子:      {metrics['profit_factor']:.3f}")
    print(f"交易天数:      {metrics['num_trading_days']}")
    print(f"最终净值:      {metrics['final_nav']:.2f}")
    print(f"{'='*60}\n")

    return metrics


def compare_with_benchmark(results: dict) -> dict:
    """
    与基准对比

    Parameters:
    -----------
    results : dict
        回测结果字典

    Returns:
    --------
    dict
        对比结果
    """
    # 策略收益
    strategy_returns = results['returns']['strategy_return']
    strategy_nav = results['nav']

    # 基准收益
    benchmark_returns = results['returns']['price_return']
    benchmark_nav = results['buy_and_hold']

    # 计算各自指标
    strategy_metrics = calculate_all_metrics(
        strategy_returns,
        strategy_nav,
        results['positions']
    )

    benchmark_metrics = calculate_all_metrics(
        benchmark_returns,
        benchmark_nav,
        pd.Series(1.0, index=benchmark_returns.index)  # 满仓
    )

    comparison = {
        'strategy': strategy_metrics,
        'benchmark': benchmark_metrics,
        'excess_return': strategy_metrics['annual_return'] - benchmark_metrics['annual_return']
    }

    return comparison


# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    np.random.seed(42)

    # 模拟收益
    returns = pd.Series(np.random.randn(500) * 0.02, index=dates)

    # 模拟净值
    nav = (1 + returns).cumprod() * 1000000

    # 模拟仓位
    positions = pd.Series(np.random.choice([0, 0.5, 1.0], size=500), index=dates)

    # 计算指标
    metrics = calculate_all_metrics(returns, nav, positions)

    print("绩效指标:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
