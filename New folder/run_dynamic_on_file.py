import json
from dynamic_step_calculator import DynamicStepCalculator

if __name__ == '__main__':
    filepath = r"c:\Users\aio\OneDrive\Desktop\DATA TRADINGVIEW\backtest\BTC\BINANCE_HBARUSDT.P, 60-TRADELIST.csv"
    calc = DynamicStepCalculator(filepath)
    report = calc.generate_comprehensive_report()
    with open('response.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print('Wrote response.json')
