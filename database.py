PLOT_BG         = '#1a1a1a'
PLOT_FG         = '#e8e8e8'
ACCENT          = '#c8f55a'
ACCENT2         = "#ff4b4b"
ACCENT3         = '#6bc5ff'
ACCENT4         = '#ffa94d'
BUTTONHOVER     = '#ff2121'
DARK            = '#666666'
DARKER          = '#2a2a2a'

# ── Sector colour palette ─────────────────────────────────────────────────────
SECTOR_COLORS = {
    "Information Technology": "#1a78c2", "Technology": "#1a78c2",
    "Health Care": "#e63946",            "Healthcare": "#e63946",
    "Financials": "#e6a817",             "Financial Services": "#e6a817",
    "Consumer Discretionary": "#f4631e",
    "Consumer Staples": "#f5c518",
    "Energy": "#b85c00",
    "Industrials": "#5b8db8",
    "Materials": "#a0522d",
    "Real Estate": "#c8a96e",            "Realestate": "#c8a96e",
    "Communication Services": "#7c4dff", "Communication": "#7c4dff",
    "Utilities": "#80c41c",
    "Government": "#2c3e8c",
    "Cash": "#1a7a3c", "Currency": "#1a7a3c",
    "Crypto": "#F7931A", "Crypto Currency": "#F7931A",
    "Other": "#444444",
}

# ── Asset group colour palette ───────────────────────────────────────────────
ASSET_GROUP_COLORS = [
    (['etf', 'stocks', 'fund', 'index', 'tracker', 'ishares', 'vanguard',
      'msci', 'sp500', 's&p', 'nasdaq', 'dow', 'russell', 'country etf',
      'sector etf', 'bond etf', 'equity etf', 'eft'],       "#1a78c2"),
    (['stock', 'equity', 'share', 'growth', 'value', 'small cap',
      'mid cap', 'large cap', 'dividend'],                    "#e63946"),
    (['cash', 'money market', 'savings', 'deposit', 'liquidity',
      'eurusd=x', 'usdeur=x', 'gbpusd=x', 'usdgbp=x', 'usdjpy=x',
      'jpyusd=x', 'usdchf=x', 'chfusd=x', 'usdcad=x', 'cadusd=x',
      'audusd=x', 'usdaud=x', 'nzdusd=x', 'usdnzd=x', 'usdsek=x',
      'usdnok=x', 'usddkk=x', 'usdpln=x', 'usdhuf=x', 'usdczk=x',
      'usdsgd=x', 'usdhkd=x', 'usdcny=x', 'usdtry=x', 'usdinr=x',
      'usdbrl=x', 'usdmxn=x', 'usdzar=x', 'usdkrw=x',
      'eurusd', 'gbpusd', 'usdjpy', 'usdchf', 'usdcad', 'audusd',
      'nzdusd', 'usd', 'eur', 'gbp', 'jpy', 'chf'],          "#1a7a3c"),
    (['bond', 'fixed income', 'treasury', 'gilt', 'note',
      'corporate bond', 'municipal', 'high yield', 'duration'],  '#2c3e8c'),
    (['reit', 'real estate', 'property', 'infrastructure'],  '#c8a96e'),
    (['commodity', 'gold', 'silver', 'oil', 'gas', 'copper',
      'wheat', 'corn', 'platinum', 'natural resource'],       '#a0522d'),
    (['crypto', 'bitcoin', 'ethereum', 'btc', 'eth', 'xrp', 'sol',
      'bnb', 'doge', 'ada', 'avax', 'btc-usd', 'eth-usd', 'usdt',
      'usdc', 'dai'],                                          '#F7931A'),
    (['forex', 'currency', 'fx', '=x', 'eurgbp=x', 'eurjpy=x'],  '#1a7a3c'),
]

# ── Country name → ISO-3166-1 alpha-3 lookup ─────────────────────────────────
_COUNTRY_ISO3 = {
    "United States":"USA","Japan":"JPN","United Kingdom":"GBR","France":"FRA",
    "Canada":"CAN","Switzerland":"CHE","Germany":"DEU","Australia":"AUS",
    "Netherlands":"NLD","Denmark":"DNK","Sweden":"SWE","Hong Kong":"HKG",
    "Spain":"ESP","Italy":"ITA","Singapore":"SGP","Finland":"FIN","Belgium":"BEL",
    "Norway":"NOR","Israel":"ISR","New Zealand":"NZL","Portugal":"PRT",
    "Ireland":"IRL","Austria":"AUT","Taiwan":"TWN","South Korea":"KOR",
    "China":"CHN","India":"IND","Brazil":"BRA","Mexico":"MEX","South Africa":"ZAF",
    "Poland":"POL","Czech Republic":"CZE","Hungary":"HUN","Greece":"GRC",
    "Malaysia":"MYS","Thailand":"THA","Indonesia":"IDN","Philippines":"PHL",
    "Saudi Arabia":"SAU","UAE":"ARE","Qatar":"QAT","Kuwait":"KWT","Egypt":"EGY",
    "Turkey":"TUR","Russia":"RUS","Chile":"CHL","Colombia":"COL","Peru":"PER",
    "Argentina":"ARG","Luxembourg":"LUX","Cayman Islands":"CYM","Bermuda":"BMU",
}

# ── Sector options ───────────────────────────────────────────────────────────
_SECTOR_OPTIONS = [
    "Information Technology", "Financials", "Health Care",
    "Industrials", "Consumer Discretionary", "Consumer Staples",
    "Communication Services", "Energy", "Materials",
    "Real Estate", "Utilities", "Government", "Currency", "Crypto", "Other",
]

# ── Known ETF country weights (normalised to sum≈1) ──────────────────────────
# Keys: uppercase base ticker without exchange suffix
_KNOWN_ETF_COUNTRIES = {
    # MSCI World trackers (IWDA, SWDA, VWCE, EUNL, FLX5, LCWD …)
    "MSCI_WORLD": {
        "United States":0.705,"Japan":0.058,"United Kingdom":0.038,"France":0.032,
        "Canada":0.030,"Switzerland":0.026,"Germany":0.023,"Australia":0.019,
        "Netherlands":0.014,"Denmark":0.009,"Sweden":0.008,"Hong Kong":0.008,
        "Spain":0.007,"Italy":0.006,"Singapore":0.004,"Finland":0.003,
        "Belgium":0.003,"Norway":0.002,"Israel":0.004,"New Zealand":0.002,
    },
    # MSCI World Infrastructure Sector Capped Index
    # Source: MSCI Index Factsheet, Jan 30, 2026
    "MSCI_INFRA": {
        "United States":0.5395,"Canada":0.123,"Japan":0.076,"Spain":0.049,
        "Germany":0.045,"United Kingdom":0.035,"Australia":0.030,
        "France":0.025,"Italy":0.020,"Netherlands":0.015,"Other":0.043,
    },
    # Franklin FTSE India / MSCI India — 100% India
    "FTSE_INDIA": {
        "India":1.00,
    },
    # S&P 500
    "SP500": {
        "United States":1.00,
    },
    # S&P 500 Paris Aligned Climate (FLX5) — 100% USA, same as SP500
    "SP500_PARIS": {
        "United States":1.00,
    },
    # MSCI Emerging Markets
    "MSCI_EM": {
        "China":0.27,"India":0.18,"Taiwan":0.18,"South Korea":0.12,
        "Brazil":0.05,"Saudi Arabia":0.04,"South Africa":0.03,"Mexico":0.02,
        "Malaysia":0.02,"Thailand":0.02,"Indonesia":0.02,"Other":0.05,
    },
    # MSCI ACWI
    "MSCI_ACWI": {
        "United States":0.635,"Japan":0.052,"United Kingdom":0.034,"France":0.029,
        "Canada":0.027,"China":0.026,"Switzerland":0.023,"Germany":0.021,
        "Australia":0.017,"Taiwan":0.017,"India":0.016,"South Korea":0.013,
        "Netherlands":0.013,"Sweden":0.007,"Denmark":0.008,"Hong Kong":0.007,
        "Spain":0.006,"Italy":0.005,"Singapore":0.004,"Brazil":0.004,
    },
    # Europe trackers
    "EUROPE": {
        "United Kingdom":0.22,"France":0.18,"Germany":0.15,"Switzerland":0.13,
        "Netherlands":0.07,"Sweden":0.06,"Denmark":0.05,"Spain":0.04,
        "Italy":0.04,"Belgium":0.02,"Finland":0.02,"Norway":0.01,"Other":0.01,
    },
    # Global Real Estate / REIT
    "GLOBAL_REIT": {
        "United States":0.63,"Japan":0.11,"Australia":0.07,"United Kingdom":0.05,
        "Singapore":0.04,"Canada":0.03,"France":0.03,"Germany":0.02,"Other":0.02,
    },
    # Nordics
    "NORDIC": {
        "Sweden":0.42,"Denmark":0.28,"Finland":0.16,"Norway":0.14,
    },
    # US Bond / Treasury — domiciled USA
    "US_BOND": {"United States":1.00},
    # Euro Bond
    "EUR_BOND": {
        "France":0.22,"Germany":0.18,"Italy":0.16,"Spain":0.12,"Netherlands":0.09,
        "Belgium":0.06,"Austria":0.04,"Portugal":0.03,"Finland":0.03,"Other":0.07,
    },
    # Global Bond
    "GLOBAL_BOND": {
        "United States":0.40,"Japan":0.10,"France":0.07,"Germany":0.07,
        "United Kingdom":0.06,"Italy":0.05,"Canada":0.04,"China":0.04,"Other":0.17,
    },
    # Commodities — by country of exchange/production
    "COMMODITY": {
        "United States":0.55,"United Kingdom":0.15,"Germany":0.10,"Other":0.20,
    },
}

# ── Known ETF sector weights ──────────────────────────────────────────────────
_KNOWN_ETF_SECTORS = {
    "MSCI_WORLD": {
        "Information Technology":0.24,"Financials":0.16,"Health Care":0.12,
        "Industrials":0.10,"Consumer Discretionary":0.10,
        "Communication Services":0.08,"Consumer Staples":0.07,
        "Energy":0.05,"Materials":0.04,"Real Estate":0.02,"Utilities":0.02,
    },
    # MSCI World Infrastructure Sector Capped Index
    # Source: MSCI Index Factsheet, Jan 30, 2026
    "MSCI_INFRA": {
        "Communication Services":0.329,"Utilities":0.326,"Energy":0.254,
        "Health Care":0.048,"Industrials":0.038,"Other":0.004,
    },
    # Franklin FTSE India / MSCI India
    # Source: Yahoo Finance FLXI.DE, Feb 2025
    "FTSE_INDIA": {
        "Financials":0.2801,"Consumer Discretionary":0.1229,"Information Technology":0.1028,
        "Energy":0.0950,"Industrials":0.0913,"Materials":0.0870,
        "Health Care":0.0600,"Consumer Staples":0.0572,
        "Communication Services":0.0487,"Utilities":0.0415,"Real Estate":0.0134,
    },
    "SP500": {
        "Information Technology":0.29,"Financials":0.13,"Health Care":0.13,
        "Consumer Discretionary":0.10,"Industrials":0.09,
        "Communication Services":0.09,"Consumer Staples":0.06,
        "Energy":0.04,"Materials":0.02,"Real Estate":0.02,"Utilities":0.02,
    },
    # S&P 500 Paris Aligned Climate — heavy tech tilt, zero energy
    # Source: Yahoo Finance FLX5.DE
    "SP500_PARIS": {
        "Information Technology":0.389,"Financials":0.142,
        "Consumer Discretionary":0.110,"Communication Services":0.105,
        "Health Care":0.102,"Consumer Staples":0.054,
        "Industrials":0.052,"Real Estate":0.022,
        "Materials":0.016,"Utilities":0.009,"Energy":0.000,
    },
    "MSCI_EM": {
        "Information Technology":0.22,"Financials":0.22,"Consumer Discretionary":0.13,
        "Communication Services":0.10,"Materials":0.09,"Energy":0.07,
        "Industrials":0.06,"Consumer Staples":0.05,"Health Care":0.04,"Utilities":0.02,
    },
    "MSCI_ACWI": {
        "Information Technology":0.24,"Financials":0.16,"Health Care":0.11,
        "Industrials":0.10,"Consumer Discretionary":0.10,
        "Communication Services":0.08,"Consumer Staples":0.07,
        "Energy":0.05,"Materials":0.04,"Real Estate":0.02,"Utilities":0.02,
    },
    "EUROPE": {
        "Financials":0.18,"Industrials":0.16,"Health Care":0.15,
        "Consumer Staples":0.12,"Consumer Discretionary":0.10,
        "Materials":0.08,"Energy":0.07,"Information Technology":0.07,
        "Utilities":0.04,"Communication Services":0.03,
    },
    "GLOBAL_REIT": {
        "Real Estate":1.00,
    },
    "NORDIC": {
        "Industrials":0.22,"Financials":0.18,"Health Care":0.14,
        "Information Technology":0.13,"Consumer Staples":0.09,
        "Materials":0.08,"Communication Services":0.07,"Energy":0.05,
        "Consumer Discretionary":0.04,
    },
    "US_BOND":     {"Financials":0.30,"Government":0.70},
    "EUR_BOND":    {"Financials":0.25,"Government":0.75},
    "GLOBAL_BOND": {"Financials":0.20,"Government":0.80},
    "COMMODITY":   {"Energy":0.35,"Materials":0.40,"Consumer Staples":0.15,"Other":0.10},
}

# ── Ticker → ETF template mapping (add more as needed) ───────────────────────
_TICKER_TO_TEMPLATE = {
    # iShares MSCI World (multiple exchange listings)
    "IWDA": "MSCI_WORLD", "IWDA.L": "MSCI_WORLD", "IWDA.AS": "MSCI_WORLD",
    "SWDA": "MSCI_WORLD", "SWDA.L": "MSCI_WORLD",
    "EUNL": "MSCI_WORLD", "EUNL.DE": "MSCI_WORLD",
    "LCWD": "MSCI_WORLD", "LCWD.L": "MSCI_WORLD",
    "VWCE": "MSCI_ACWI",  "VWCE.DE": "MSCI_ACWI",  "VWCE.L": "MSCI_ACWI",
    # FLX5 = Franklin S&P 500 Paris Aligned Climate UCITS ETF (100% USA, zero energy)
    "FLX5": "SP500_PARIS", "FLX5.DE": "SP500_PARIS", "FLX5.L": "SP500_PARIS",
    "FLX5.AS": "SP500_PARIS", "FLX5.SW": "SP500_PARIS", "FLX5.F": "SP500_PARIS",
    # FLXI = Franklin FTSE India UCITS ETF (100% India)
    "FLXI": "FTSE_INDIA", "FLXI.DE": "FTSE_INDIA", "FLXI.L": "FTSE_INDIA",
    "FLXI.AS": "FTSE_INDIA", "FLXI.SW": "FTSE_INDIA", "FLXI.F": "FTSE_INDIA",
    # S&P 500
    "SPY": "SP500", "VOO": "SP500", "IVV": "SP500", "CSPX": "SP500",
    "CSPX.L": "SP500", "SXR8": "SP500", "SXR8.DE": "SP500",
    "IUSA": "SP500", "IUSA.L": "SP500",
    # ACWI
    "ACWI": "MSCI_ACWI", "ISAC": "MSCI_ACWI", "ISAC.L": "MSCI_ACWI",
    # Emerging Markets
    "EEM": "MSCI_EM", "VWO": "MSCI_EM", "EIMI": "MSCI_EM", "EIMI.L": "MSCI_EM",
    "IEEM": "MSCI_EM", "IEEM.L": "MSCI_EM",
    # Europe
    "VGK": "EUROPE", "IEUR": "EUROPE", "EZU": "EUROPE",
    "IMEU": "EUROPE", "IMEU.L": "EUROPE",
    "MEUD": "EUROPE", "MEUD.L": "EUROPE",
    # Nordics
    "NORDEN": "NORDIC",
    # Global REIT
    "REET": "GLOBAL_REIT", "IWDP": "GLOBAL_REIT", "IWDP.L": "GLOBAL_REIT",
    # Bonds
    "AGG": "US_BOND", "BND": "US_BOND", "TLT": "US_BOND",
    "IEAG": "EUR_BOND", "IEAG.L": "EUR_BOND",
    "IGLO": "GLOBAL_BOND", "IGLO.L": "GLOBAL_BOND",
    # Commodities
    "GLD": "COMMODITY", "IAU": "COMMODITY", "PHAU": "COMMODITY",
    "PDBC": "COMMODITY", "DJP": "COMMODITY",
}

# Sector name synonyms — normalise to canonical name before aggregation
_SECTOR_NORM = {
    "Financial Services": "Financials",
    "Technology": "Information Technology",
    "Healthcare": "Health Care",
    "Realestate": "Real Estate",
    "Communication": "Communication Services",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    "Basic Materials": "Materials",
    "Cash":"Currency",
}