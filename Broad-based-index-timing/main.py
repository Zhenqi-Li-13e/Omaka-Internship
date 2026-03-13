"""
宽基ETF轮动策略 - 主程序（简化版）

使用方法:
    python main.py

功能:
    1. 加载10个ETF数据
    2. 生成效率动量轮动信号
    3. 执行回测
    4. 输出绩效指标
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
matplotlib.use('Agg')

# 导入自定义模块
from data_loader import get_all_etf_data, save_etf_data, load_etf_data, align_etf_data
from backtest import backtest_rotation_strategy


# ETF 配置
# type: 'A' = A股ETF, 'CROSS' = 跨境ETF
ETF_INFO = {
    '000015': {'name': '红利低波', 'type': 'A'},
    '000016': {'name': '上证50ETF', 'type': 'A'},
    '000300': {'name': '沪深300ETF', 'type': 'A'},
    '000688': {'name': '科创50ETF', 'type': 'A'},
    '000852': {'name': '中证1000ETF', 'type': 'A'},
    '000905': {'name': '中证500ETF', 'type': 'A'},
    '399006': {'name': '创业板ETF', 'type': 'A'},
    '518880': {'name': '黄金ETF', 'type': 'A'},
    'NDX': {'name': '纳指100ETF', 'type': 'CROSS'},
    'SPX': {'name': '标普500ETF', 'type': 'CROSS'},
}

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(PROJECT_ROOT, 'data')
RESULTS_FOLDER = os.path.join(PROJECT_ROOT, 'results')


def plot_rotation_results(results: dict, output_dir: str | None = None) -> None:
    """绘制轮动策略结果图表"""
    if output_dir is None:
        output_dir = RESULTS_FOLDER

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    nav = results['nav']
    hs300_nav = results['buy_and_hold']
    equal_weight_nav = results['equal_weight_nav']

    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    # 1. 净值曲线对比
    ax1 = axes[0]
    ax1.plot(nav.index, nav.values, label='轮动策略', linewidth=1.5, color='blue')
    ax1.plot(hs300_nav.index, hs300_nav.values, label='沪深300', linewidth=1.5, color='orange', alpha=0.7)
    ax1.plot(equal_weight_nav.index, equal_weight_nav.values, label='等权组合', linewidth=1.5, color='green', alpha=0.5)
    ax1.set_title('轮动策略 vs 基准对比', fontsize=14)
    ax1.set_xlabel('日期')
    ax1.set_ylabel('净值')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # 2. 回撤曲线
    ax2 = axes[1]
    peak = nav.expanding().max()
    drawdown = (nav - peak) / peak * 100
    ax2.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
    ax2.plot(drawdown.index, drawdown.values, color='red', linewidth=1)
    ax2.set_title('策略回撤曲线', fontsize=14)
    ax2.set_xlabel('日期')
    ax2.set_ylabel('回撤 (%)')
    ax2.grid(True, alpha=0.3)

    # 3. 仓位变化
    ax3 = axes[2]
    positions = results['positions']
    for etf_code in positions.columns:
        name = ETF_INFO.get(etf_code, {}).get('name', etf_code)
        ax3.fill_between(positions.index, positions[etf_code].values * 100, 0, alpha=0.3, label=name)
    ax3.set_title('各ETF仓位变化', fontsize=14)
    ax3.set_xlabel('日期')
    ax3.set_ylabel('仓位 (%)')
    ax3.legend(loc='upper left', fontsize=8)
    ax3.set_ylim(-5, 105)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    filename = f"{output_dir}/rotation_backtest.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {filename}")


def run_rotation_analysis(start_date: str = '2014-01-01',
                         end_date: str | None = None,
                         initial_capital: float = 1000000.0,
                         use_cache: bool = True,
                         output_dir: str | None = None) -> dict:
    """运行轮动策略分析（简化版）"""
    print("\n" + "=" * 70)
    print("宽基ETF轮动策略（简化版）")
    print("=" * 70)

    if output_dir is None:
        output_dir = RESULTS_FOLDER

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. 数据获取
    print("\n[1/4] 获取ETF数据...")

    data = {}
    if use_cache:
        data = load_etf_data(DATA_FOLDER)
        if len(data) > 0:
            print(f"  从缓存加载了 {len(data)} 个ETF数据")

    if len(data) < len(ETF_INFO):
        data = get_all_etf_data(start_date, end_date)
        if len(data) > 0:
            save_etf_data(data, DATA_FOLDER)

    if len(data) == 0:
        print("错误: 未能获取任何ETF数据")
        return {}

    data = align_etf_data(data)

    print(f"\n成功获取 {len(data)} 个ETF数据")
    for code, df in data.items():
        name = ETF_INFO.get(code, {}).get('name', code)
        print(f"  {name}: {len(df)} 条记录")

    # 2. 策略参数
    momentum_window = 20
    top_n = 2

    print("\n[2/4] 策略参数:")
    print(f"  动量窗口: {momentum_window}天")
    print(f"  选择Top N: {top_n}")
    print(f"  总仓位: 100%（每只50%，满仓）")
    print(f"  交易成本:")
    print(f"    - A股ETF单边: 手续费0.01% + 滑点0.02% = 0.03%")
    print(f"    - 跨境ETF单边: 手续费0.02% + 滑点0.02% = 0.04%")
    print(f"    - 买入/卖出各扣一次")

    # 3. 运行回测
    print("\n[3/4] 运行回测...")

    results = backtest_rotation_strategy(
        data,
        momentum_window=momentum_window,
        top_n=top_n,
        initial_capital=initial_capital,
        etf_info=ETF_INFO
    )

    if not results:
        print("错误: 回测失败")
        return {}

    # 4. 计算绩效指标
    print("\n[4/4] 计算绩效指标...")

    returns = results['returns']['net_return']
    nav = results['nav']
    positions = results['positions'].sum(axis=1)

    # 策略指标
    total_return = nav.iloc[-1] / nav.iloc[0] - 1
    annual_return = (1 + total_return) ** (252 / len(nav)) - 1
    volatility = returns.std() * np.sqrt(252)
    sharpe = annual_return / volatility if volatility > 0 else 0
    peak = nav.expanding().max()
    max_drawdown = ((nav - peak) / peak).min()

    # 计算绩效指标
    initial_capital = results['initial_capital']
    dates = results['nav'].index
    years = len(dates) / 252

    strategy_total = results['nav'].iloc[-1] / initial_capital - 1
    strategy_annual = (1 + strategy_total) ** (1 / years) - 1

    hs300_total = results['buy_and_hold'].iloc[-1] / initial_capital - 1
    hs300_annual = (1 + hs300_total) ** (1 / years) - 1

    equal_total = results['equal_weight_nav'].iloc[-1] / initial_capital - 1
    equal_annual = (1 + equal_total) ** (1 / years) - 1

    excess_hs300_total = strategy_total - hs300_total
    excess_hs300_annual = strategy_annual - hs300_annual
    excess_equal_total = strategy_total - equal_total
    excess_equal_annual = strategy_annual - equal_annual

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
            strategy_total, strategy_annual,
            hs300_total, hs300_annual,
            equal_total, equal_annual,
            excess_hs300_total, excess_hs300_annual,
            excess_equal_total, excess_equal_annual
        ]
    }
    perf_df = pd.DataFrame(perf_data)
    perf_df.to_csv(f'{output_dir}/performance_summary.csv', index=False, encoding='utf-8-sig')

    # 控制台输出
    print("\n" + "=" * 60)
    print("                         绩效总结")
    print("=" * 60)
    print(f"{'指标':<25}{'轮动策略':>12}{'沪深300':>12}{'等权组合':>12}")
    print("-" * 60)
    print(f"{'区间累计总收益':<25}{strategy_total*100:>11.2f}%{hs300_total*100:>11.2f}%{equal_total*100:>11.2f}%")
    print(f"{'年化收益率':<25}{strategy_annual*100:>11.2f}%{hs300_annual*100:>11.2f}%{equal_annual*100:>11.2f}%")
    print("=" * 60)
    print(f"{'超额收益(vs沪深300) - 总收益差值':<30}{excess_hs300_total*100:>14.2f}%")
    print(f"{'超额收益(vs沪深300) - 年化收益差值':<30}{excess_hs300_annual*100:>14.2f}%")
    print("-" * 60)
    print(f"{'超额收益(vs等权组合) - 总收益差值':<30}{excess_equal_total*100:>14.2f}%")
    print(f"{'超额收益(vs等权组合) - 年化收益差值':<30}{excess_equal_annual*100:>14.2f}%")
    print("=" * 60)
    print(f"\n[绩效已保存至 {output_dir}/performance_summary.csv]")

    print("\n" + "=" * 70)
    print("绩效报告")
    print("=" * 70)
    print(f"\n【策略绩效】")
    print(f"  年化收益率: {annual_return:.2%}")
    print(f"  年化波动率: {volatility:.2%}")
    print(f"  Sharpe比率: {sharpe:.3f}")
    print(f"  最大回撤: {max_drawdown:.2%}")
    print("\n" + "=" * 70)

    # 5. 保存结果
    print("\n保存结果...")

    nav_df = pd.DataFrame({
        'strategy_nav': results['nav'],
        'hs300_nav': results['buy_and_hold'],
        'equal_weight_nav': results['equal_weight_nav']
    })
    nav_file = f"{output_dir}/rotation_nav.csv"
    nav_df.to_csv(nav_file)
    print(f"净值数据已保存: {nav_file}")

    positions_file = f"{output_dir}/rotation_positions.csv"
    results['positions'].to_csv(positions_file)
    print(f"仓位数据已保存: {positions_file}")

    # 6. 绘制图表
    print("\n绘制图表...")
    plot_rotation_results(results, output_dir)

    print("\n" + "=" * 70)
    print("分析完成!")
    print("=" * 70)

    return results


def main():
    """主函数"""
    start_date = '2014-01-01'
    end_date = '2025-12-31'
    initial_capital = 1000000.0

    print("宽基ETF轮动策略")
    print("=" * 50)
    print("10个ETF: 上证50, 沪深300, 中证500, 中证1000,")
    print("        创业板, 科创50, 纳指100, 标普500,")
    print("        黄金ETF, 红利低波")
    print(f"回测周期: {start_date} ~ {end_date}")
    print(f"初始资金: {initial_capital:,.0f}")
    print("=" * 50)

    try:
        results = run_rotation_analysis(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            use_cache=True,
            output_dir=RESULTS_FOLDER
        )

        if results:
            print("\n回测成功完成!")
        else:
            print("\n回测失败!")

    except KeyboardInterrupt:
        print("\n\n用户中断程序")
    except Exception as e:
        print(f"\n\n程序错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
