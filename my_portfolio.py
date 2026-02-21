from datetime import datetime, timedelta

# Create a dictionary of tickers and weights
tickers = ['FLX5.DE', 'FLXI.DE', 'MANTA.HE', 'EURUSD=X']
weights = [0.698, 0.169, 0.124, 0.009]
portfolio = dict(zip(tickers, weights))
print('Portfolio:', portfolio)

# Remember to change asset classes accoring to your portfolio
asset_classes = dict(zip(tickers, ['International ETF', 'International ETF', 'Stock', 'Cash']))

# Define the start date and end date
start_date = '1997-01-01'
end_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
print('Start Date:', start_date)
print('End Date  :', end_date)

# Define the risk-free rate:
risk_free_rate = 0.02
print('Risk-free Rate:', risk_free_rate)