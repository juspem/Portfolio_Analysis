from datetime import datetime, timedelta

# Create a dictionary of tickers and weights
tickers = ['FLX5.DE','FLXI.DE','MANTA.HE','EURUSD=X','XRP-EUR','XLM-EUR','ALGO-EUR','DOT-EUR']
weights = [0.66043507817811,0.15992522093813733,0.11769204622705642,0.00773283480625425,0.046906866077498295,0.004843643779741672,0.0015295717199184228,0.0009347382732834807]
portfolio = dict(zip(tickers, weights))
print('Portfolio:', portfolio)

# Remember to change asset classes accoring to your portfolio
asset_classes = dict(zip(tickers, ['USA Stocks','India Stocks','Stock','Cash','Crypto','Crypto','Crypto','Crypto']))

# Define the start date and end date
start_date = '2000-01-01'
end_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
print('Start Date:', start_date)
print('End Date  :', end_date)

# Define the risk-free rate:
risk_free_rate = 0.02
print('Risk-free Rate:', risk_free_rate)

# Investment amounts for FI calculations
initial_investment = 10000  # Initial portfolio value in dollars
monthly_investment = 400    # Monthly contribution in dollars
print('Initial Investment:', initial_investment)
print('Monthly Investment:', monthly_investment)

# Custom annualized return for FI forecasting (optional override)
# Set to None to use historical return, or set a custom value (e.g., 0.07 for 7%)
custom_annualized_return = 0.10
print('Custom Annualized Return:', custom_annualized_return)

# Safe Withdrawal Rate (SWR) for Financial Independence calculations
# The percentage of portfolio that can be withdrawn annually in retirement
# Set to 0 to disable SWR-based FI goal calculations
safe_withdrawal_rate = 0
print('Safe Withdrawal Rate:', safe_withdrawal_rate)