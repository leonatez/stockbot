#Import VNSTOCK
from vnstock import Vnstock

#We need to initiate the stock instance before using any function below:
stock = Vnstock().stock(symbol='ACB', source='VCI') #please always keep source='VCI'

#Please use this function whenever we need to get a full list of stocks with all attributes. It returns a pandas DataFrame containing a list of all listed stock symbols from all Vietnamese stock exchanges (e.g., HSX, HNX, UPCOM).

    The returned table includes metadata for each stock symbol, including:

    - `symbol`: Stock ticker symbol (e.g., 'YEG', 'XPH')
    - `exchange`: Name of the stock exchange (e.g., 'HSX', 'UPCOM')
    - `organ_short_name`: Short name of the issuing organization
    - `organ_name`: Full legal name of the issuing organization
    - `isVN30`: Boolean flag indicating if the stock is part of the VN30 index
    - `icb_name1` to `icb_name4`: Industry classification labels at different hierarchical levels 
       based on ICB (Industry Classification Benchmark), from general sector to specific sub-sector.

    This data is typically used for filtering, grouping, or analyzing listed stocks by sector, exchange,
    or index membership.


def all_stocks():
    by_exchange = stock.listing.symbols_by_exchange()
    by_industries = stock.listing.symbols_by_industries()
    by_industries.drop(columns=['organ_name', 'icb_name3','icb_name2','icb_name4','com_type_code'], inplace=True)
    vn30_list = stock.listing.symbols_by_group('VN30')
    vn30_symbols = set(vn30_list.tolist()) if vn30_list is not None else set()
    merged_data = pd.merge(by_exchange, by_industries, on='symbol', how='inner')
    merged_data['isVN30'] = merged_data['symbol'].apply(lambda x: x in vn30_symbols)
    icb_mapping = stock.listing.industries_icb()
    icb_dict = {}
    for level in [1, 2, 3, 4]:
                level_data = icb_mapping[icb_mapping['level'] == level]
                icb_dict[level] = dict(zip(level_data['icb_code'], level_data['icb_name']))
    result_df = merged_data.copy()
    for level in [1, 2, 3, 4]:
        code_col = f'icb_code{level}'
        name_col = f'icb_name{level}'
                
        if code_col in result_df.columns:
            result_df[name_col] = result_df[code_col].map(icb_dict[level]).fillna('Unknown')
        else:
            print(f"Warning: {code_col} not found in dataframe")
    result_df.drop(columns=['icb_code1', 'icb_code2', 'icb_code3','icb_code4','type','product_grp_id'], inplace=True)
    return result_df

#VNSTOCK support to get quote history of a stock. This function will return time (yyyy-mm-dd), open, high, low, close and volume
stock = Vnstock().stock(symbol='ACB', source='VCI') #please always keep source='VCI', just replace symbol for the correct symbol we wanna check quote
df = stock.quote.history(start='2024-01-01', end='2025-03-19', interval='1D') #replace the 'start' to the latest date our database has value to avoid query too much, and replace the 'end' to today

#AUTOMATIC STOCK PRICE UPDATE WORKFLOW
#After AI analysis identifies mentioned stocks, the system automatically fetches their price history.
#The stock_price_updater.py module handles this by:
#1. Extracting unique stock symbols from AI analysis results
#2. Checking the latest date we have price data for each stock in database
#3. Fetching quote history from the day after latest data to today (optimized queries)
#   - If no existing data: fetches from 2024-01-01 to today
#   - If existing data: fetches from latest date + 1 day to today
#4. Saving new price data to stock_prices table with upsert to handle duplicates
#5. This runs automatically after every /crawl and /crawl-multiple API call

#DAILY VN30 UPDATE WORKFLOW
#This function gets the current VN30 stock list and is integrated into the daily analysis workflow
listing = Listing()
vn30_list = listing.symbols_by_group('VN30')  #Returns a pandas Series of current VN30 stocks
vn30_symbols = set(vn30_list.tolist()) if vn30_list is not None else set()

#The daily_vn30_update.py script automatically:
#1. Fetches current VN30 symbols using the above function
#2. Resets all stocks isvn30=False 
#3. Updates VN30 stocks to isvn30=True
#4. This runs at the start of every /crawl and /crawl-multiple API call


#GET MORE COMPANY INFORMATION
#Initiate company instance:
from vnstock.explorer.vci import Company
company = Company('ACB') #Replace 'ACB' by actual stock symbol we want to check

#GET number of issue share by this function
company.overview() #this will return a dataframe of stock symbol, including columns 'symbol', 'issue_share', 'charter_capital'. Just care those columns and ignore the remaining columns.

#GET company events by this function:
company.events() #this will return a dataframe of the stock symbol, including all columns in table stock_events. This is the source of info to insert to table stock_events.

#GET company dividend summary: This function we need to initiate a different company instance than other functions:
company = Vnstock().stock(symbol='VIN', source='TCBS').company #keep the source is always 'TCBS', while replace symbols 'VIN' to the symbol we want to check
company.dividends() #this will return a dataframe of the stock dividend, including 'exercise_date','cash_year','cash_dividend_percentage','issue_method'

#COMPANY FINANCE
Finance is one of the most important part of stock analysis. Let's explore what do we have in VNStock with following functions:
#Get financial condition of a company
from vnstock import Vnstock
stock = Vnstock().stock(symbol='VIN', source='VCI') #Keep source from VCI, just change 'VIN' to symbol we want to explore
stock.finance.balance_sheet(period='quarter', lang='vi', dropna=True) #get balance sheet
stock.finance.income_statement(period='quarter', lang='vi', dropna=True) #get P&L
stock.finance.cash_flow(period='quarter', dropna=True) #get cashflow
stock.finance.income_statement(period='quarter', lang='vi', dropna=True) #get income statement
stock.finance.ratio(period='quarter', lang='vi', dropna=True) #Get all basic ratio of the company like revenue, revenue growth, net profit, etc 