#!/usr/bin/env python
# coding: utf-8

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objs as go

from dash.dependencies import Input, Output
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Dash app with a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
server = app.server  # Expose the Flask server

# Define the layout of the app
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Advanced Trading Strategy Analyzer", className="text-center text-primary"), className="mb-4 mt-4")
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Input Parameters", className="card-title"),
                    
                    dbc.Label("Ticker Symbol (without .SR for Saudi stocks):"),
                    dcc.Input(id='ticker-input', type='text', value='1303', className="mb-3", style={'width': '100%'}),
                    
                    dbc.Label("Period:"),
                    dcc.Dropdown(
                        id='period-input',
                        options=[
                            {'label': '1 Year', 'value': '1y'},
                            {'label': '2 Years', 'value': '2y'},
                            {'label': '5 Years', 'value': '5y'},
                            {'label': 'All', 'value': 'max'}
                        ],
                        value='1y',
                        className="mb-3",
                        style={'width': '100%'}
                    ),
                    
                    dbc.Label("Short SMA Period:"),
                    dcc.Input(id='sma-short-input', type='number', value=7, className="mb-3", style={'width': '100%'}),
                    
                    dbc.Label("Long SMA Period:"),
                    dcc.Input(id='sma-long-input', type='number', value=10, className="mb-3", style={'width': '100%'}),
                    
                    dbc.Label("RSI Threshold:"),
                    dcc.Input(id='rsi-threshold-input', type='number', value=40, className="mb-3", style={'width': '100%'}),
                    
                    dbc.Label("Short ADL SMA Period:"),
                    dcc.Input(id='adl-short-input', type='number', value=19, className="mb-3", style={'width': '100%'}),
                    
                    dbc.Label("Long ADL SMA Period:"),
                    dcc.Input(id='adl-long-input', type='number', value=25, className="mb-3", style={'width': '100%'}),
                    
                    dbc.Button("Analyze", id="analyze-button", color="primary", className="mt-3", style={'width': '100%'})
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Trading Strategy Graph", className="card-title"),
                    dcc.Graph(id='trading-graph')
                ])
            ])
        ], width=9)
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Best Strategy Summary", className="card-title"),
                    html.Pre(id='summary-output', style={'whiteSpace': 'pre-wrap', 'font-family': 'monospace'})
                ])
            ])
        ], width=12)
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H4("Best Trades Details", className="card-title"),
                    html.Div(id='trades-table')
                ])
            ])
        ], width=12)
    ])
], fluid=True)

@app.callback(
    [Output('trading-graph', 'figure'),
     Output('summary-output', 'children'),
     Output('trades-table', 'children')],
    [Input('analyze-button', 'n_clicks')],
    [Input('ticker-input', 'value'),
     Input('period-input', 'value'),
     Input('sma-short-input', 'value'),
     Input('sma-long-input', 'value'),
     Input('rsi-threshold-input', 'value'),
     Input('adl-short-input', 'value'),
     Input('adl-long-input', 'value')]
)
def update_graph(n_clicks, ticker_input, period, sma_short, sma_long, rsi_threshold, adl_short, adl_long):
    try:
        if n_clicks is None:
            # Initial call, return empty outputs
            return go.Figure(), "Awaiting input parameters.", ""
        
        logger.info("Received input parameters.")
        logger.info(f"Ticker Input: {ticker_input}")
        logger.info(f"Period: {period}")
        logger.info(f"SMA Short: {sma_short}")
        logger.info(f"SMA Long: {sma_long}")
        logger.info(f"RSI Threshold: {rsi_threshold}")
        logger.info(f"ADL Short SMA: {adl_short}")
        logger.info(f"ADL Long SMA: {adl_long}")
        
        # Validate inputs
        if sma_short >= sma_long:
            raise ValueError("Short SMA period must be less than Long SMA period.")
        if adl_short >= adl_long:
            raise ValueError("Short ADL SMA period must be less than Long ADL SMA period.")
        
        # Determine ticker symbol
        if ticker_input.isdigit():
            ticker = f"{ticker_input}.SR"
        else:
            ticker = ticker_input

        logger.info(f"Using ticker symbol: {ticker}")

        # Download data
        logger.info("Downloading data...")
        df = yf.download(ticker, period=period)
        
        if df.empty:
            raise ValueError(f"No data found for ticker symbol: {ticker}")

        df.index = pd.to_datetime(df.index)
        logger.info("Data downloaded successfully.")
        
        # Calculate Simple Moving Averages (SMA)
        df['SMA_Short'] = df['Close'].rolling(window=sma_short).mean()
        df['SMA_Long'] = df['Close'].rolling(window=sma_long).mean()
        logger.info("Calculated SMAs.")
        
        # Calculate RSI using pandas_ta
        df['RSI'] = ta.rsi(df['Close'], length=14)
        logger.info("Calculated RSI.")
        
        # Calculate MACD using pandas_ta
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df = pd.concat([df, macd], axis=1)
        logger.info("Calculated MACD.")
        
        # Calculate Accumulation/Distribution Line (ADL) using pandas_ta
        df['ADL'] = ta.ad(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'])
        logger.info("Calculated ADL.")
        
        # Calculate ADL Short and Long SMAs
        df['ADL_Short_SMA'] = df['ADL'].rolling(window=adl_short).mean()
        df['ADL_Long_SMA'] = df['ADL'].rolling(window=adl_long).mean()
        logger.info("Calculated ADL SMAs.")
        
        # Drop rows with NaN values created by rolling calculations
        df.dropna(inplace=True)
        logger.info("Dropped NaN values.")
        
        # Signal generation
        logger.info("Generating trading signals.")
        df['Signal'] = df.apply(
            lambda row: -1 if (
                row['Close'] >= row['SMA_Short'] and
                row['SMA_Short'] > row['SMA_Long'] and
                row['ADL_Short_SMA'] > row['ADL_Long_SMA'] and
                row['RSI'] >= rsi_threshold and
                row['MACD_12_26_9'] > row['MACDs_12_26_9']
            ) else (
                1 if (
                    row['Close'] < row['SMA_Short'] and
                    row['SMA_Short'] < row['SMA_Long']
                ) else 0
            ), axis=1
        )
        logger.info("Trading signals generated.")
        
        # Simulate trading
        logger.info("Simulating trades.")
        initial_investment = 100000
        portfolio = initial_investment
        trades = []
        buy_price = None
        trade_start = None
        number_of_trades = 0

        for index, row in df.iterrows():
            if row['Signal'] == 1 and buy_price is None:
                buy_price = row['Close']
                trade_start = index
                number_of_trades += 1
                logger.info(f"Buy signal at {index.date()} | Price: {buy_price}")
            elif row['Signal'] == -1 and buy_price is not None:
                sell_price = row['Close']
                shares = portfolio / buy_price
                profit = (sell_price - buy_price) * shares
                portfolio += profit
                days_held = (index - trade_start).days

                trades.append({
                    'Sell Date': index.date().strftime('%Y-%m-%d'),
                    'Buy Price': f"{buy_price:.2f} SAR",
                    'Sell Price': f"{sell_price:.2f} SAR",
                    'Days Held': days_held,
                    'Profit': f"{profit:,.2f} SAR",
                    'Profit Percentage': f"{(profit / (portfolio - profit)) * 100:.2f}%"
                })
                logger.info(f"Sell signal at {index.date()} | Price: {sell_price} | Profit: {profit:.2f} SAR | Days Held: {days_held}")
                
                buy_price = None

        final_value = portfolio
        total_return = final_value - initial_investment
        percentage_return = (total_return / initial_investment) * 100
        average_days = (sum([t['Days Held'] for t in trades]) / number_of_trades) if number_of_trades > 0 else 0

        logger.info("Trade simulation completed.")
        logger.info(f"Final Portfolio Value: {final_value:.2f} SAR")
        logger.info(f"Total Return: {total_return:.2f} SAR")
        logger.info(f"Percentage Return: {percentage_return:.2f}%")
        logger.info(f"Number of Trades: {number_of_trades}")
        logger.info(f"Average Days Held per Trade: {average_days:.2f} days")

        # Create the plot with enhanced visuals
        logger.info("Creating trading strategy graph.")
        fig = go.Figure()

        # Add the Closing Price and SMA lines
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_Short'], mode='lines', name=f'SMA Short ({sma_short})', line=dict(color='orange', dash='dash')))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_Long'], mode='lines', name=f'SMA Long ({sma_long})', line=dict(color='green', dash='dot')))

        # Highlight Buy and Sell signals
        buy_signals = df[df['Signal'] == 1]
        sell_signals = df[df['Signal'] == -1]

        fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='Buy Signal', 
                                 marker=dict(color='green', size=12, symbol='triangle-up')))
        fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='Sell Signal', 
                                 marker=dict(color='red', size=12, symbol='triangle-down')))

        fig.update_layout(title=f'Trading Strategy for {ticker}', xaxis_title='Date', yaxis_title='Price (SAR)', template='plotly_white')

        # Prepare the summary text
        summary_text = (
            f"**Ticker:** {ticker}\n"
            f"**Initial Investment:** {initial_investment:,.2f} SAR\n"
            f"**Final Portfolio Value:** {final_value:,.2f} SAR\n"
            f"**Total Return:** {total_return:,.2f} SAR\n"
            f"**Percentage Return:** {percentage_return:.2f}%\n"
            f"**Number of Trades:** {number_of_trades}\n"
            f"**Average Days Held per Trade:** {average_days:.2f} days"
        )

        # Create the trades table
        if trades:
            trades_df = pd.DataFrame(trades)
            trades_table = dbc.Table.from_dataframe(trades_df, striped=True, bordered=True, hover=True)
        else:
            trades_table = html.Div("No trades executed based on the current strategy parameters.")

        logger.info("Graph, summary, and trades table created successfully.")

        return fig, summary_text, trades_table

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        logger.error(f"Error in update_graph: {e}", exc_info=True)
        # Return empty outputs with error message
        return go.Figure(), error_msg, ""

if __name__ == '__main__':
    app.run_server(debug=True)
