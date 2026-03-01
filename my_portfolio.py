from datetime import datetime, timedelta

# Create a dictionary of tickers and weights
tickers = ['SPY','QQQ']
weights = [0.60,0.40]
portfolio = dict(zip(tickers, weights))

# Remember to change asset classes accoring to your portfolio
asset_classes = dict(zip(tickers, ['USA Stocks','USA Stocks']))

# Define the start date and end date
start_date = '2000-01-01'
end_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

# Define the risk-free rate:
risk_free_rate = 0.02

# Investment amounts for FI calculations
initial_investment = 10000  # Initial portfolio value in dollars
monthly_investment = 400    # Monthly contribution in dollars

# Custom annualized return for FI forecasting (optional override)
# Set to None to use historical return, or set a custom value (e.g., 0.07 for 7%)
custom_annualized_return = 0.10

# Safe Withdrawal Rate (SWR) for Financial Independence calculations
# The percentage of portfolio that can be withdrawn annually in retirement
# Set to 0 to disable SWR-based FI goal calculations
safe_withdrawal_rate = 0