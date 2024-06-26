# Standard library imports
import itertools

# Third-party imports for data handling
import pandas as pd
import numpy as np

# Third-party imports for plotting and visualization
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters
from pylab import rcParams

# Third-party imports for statistical modeling
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from scipy.signal import periodogram
import ruptures as rpt

# Third-party imports for machine learning metrics
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

# Import data
file_path = '/Users/apple/Downloads/prc_hicp_manr__custom_7843973_linear.csv'
data = pd.read_csv(file_path)

data.head()
data.tail()

# See the data types and non-missing values
data.info()

# Cleaning and Formatting
data = data.drop(['DATAFLOW', 'LAST UPDATE', 'freq', 'unit', 'geo', 'OBS_FLAG', 'coicop'], axis=1). \
    rename(columns={'TIME_PERIOD': 'Date', 'OBS_VALUE': 'Rate'})

# Converting the data column into datetime format
data['Date'] = pd.to_datetime(data['Date'])
data.set_index('Date', inplace=True)
data = data.resample('MS').mean()

# Stationary Check
# ADF Test
def adf_test(series):
    result = adfuller(series, regression='c', autolag='AIC')
    print('====Augmented Dickey-Fuller Test Results====\n')
    print(f'ADF Statistic: {result[0]:.6f}')
    print(f'p-value: {result[1]:.6f}')
    print(f'# Lags used: {result[2]}')
    print(f'Number of observations: {result[3]}')
    print('Critical values:')
    for key, value in result[4].items():
        print(f'\t{key}: {value:.6f}')

    # Simplifying the logic for rejecting the null hypothesis
    if result[1] < 0.05:
        print('\nReject the null hypothesis. Data has no unit root and is stationary.')
    else:
        print('\nCannot reject the null hypothesis. Data may have a unit root and be non-stationary.')

adf_test(data['Rate'])

# KPSS Test
# Perform the KPSS test on the 'Rate' column
result = kpss(data['Rate'])

print('======= Kwiatkowski-Phillips-Schmidt-Shin (KPSS) Test Results =======\n')
print("KPSS Test Statistic:", result[0])
print("p-value:", result[1])
print("# Lags used: ", result[2])
print("Critical Values:")
for key, value in result[3].items():
    print(f"\t{key}: {value}")

# Interpretation of the KPSS test results
critical_value = result[3]['5%']
if result[0] > critical_value:
    print('\nStrong evidence against the null hypothesis, we reject the null hypothesis. Data is non-stationary.')
else:
    print('\nWeak evidence against rejecting the null hypothesis. Data has no unit root and is stationary.')

# ACF and PACF
f, ax = plt.subplots(nrows=2, ncols=1, figsize=(12, 8))
plot_acf(data['Rate'], lags=20, ax=ax[0])
plot_pacf(data['Rate'], lags=20, ax=ax[1], method='ols')

ax[1].annotate('Strong correlation at lag = 1', xy=(1, 0.36), xycoords='data',
               xytext=(0.15, 0.7), textcoords='axes fraction',
               arrowprops=dict(color='red', shrink=0.05, width=1))

ax[1].annotate('Strong correlation at lag = 2', xy=(2.1, -0.5), xycoords='data',
               xytext=(0.25, 0.1), textcoords='axes fraction',
               arrowprops=dict(color='red', shrink=0.05, width=1))
plt.tight_layout()
plt.show()

# Cyclic Behavior Detection: Frequency vs. periodogram
fs = 1 / 12  # The sampling frequency. For monthly data, it would be 1 sample per month.
# Compute the periodogram
frequencies, power = periodogram(data['Rate'], fs=fs)

# Print the first few values
print("Frequency\tPower")
for freq, pwr in zip(frequencies[:10], power[:10]):  # Adjust the slice as needed
    print(f"{freq:.4f}\t\t{pwr:.4f}")

# Find the index of the maximum power
max_power_index = np.argmax(power)
max_frequency = frequencies[max_power_index]
max_power = power[max_power_index]

print(f"Peak Frequency: {max_frequency:.4f}")
print(f"Peak Power: {max_power:.4f}")

# Plot the frequency vs. power periodogram for cyclic behavior
plt.plot(frequencies, power)
plt.xlabel('Frequency')
plt.ylabel('Power')
plt.title('Frequency vs. Power Periodogram')
plt.show()

# Function to transform and check stationarity
def transformation(series):
    # Differencing the series
    diff_series = series.diff().dropna()

    # Register the converters for matplotlib
    register_matplotlib_converters()

    # Plot the transformed (differenced) series
    fig = plt.figure(figsize=(16, 6))

    ax1 = fig.add_subplot(1, 3, 1)
    ax1.set_title('Transformed Series')
    ax1.plot(diff_series, label='Differenced Series')
    ax1.plot(diff_series.rolling(window=12).mean(), color='crimson', label='Rolling Mean')
    ax1.plot(diff_series.rolling(window=12).std(), color='black', label='Rolling Std')
    ax1.legend()

    # Autocorrelation Plot
    ax2 = fig.add_subplot(1, 3, 2)
    plot_acf(diff_series, ax=ax2, lags=50, title='Autocorrelation')
    ax2.axhline(y=-1.96 / np.sqrt(len(diff_series)), linestyle='--', color='gray')
    ax2.axhline(y=1.96 / np.sqrt(len(diff_series)), linestyle='--', color='gray')
    ax2.set_xlabel('Lags')

    # Partial Autocorrelation Plot
    ax3 = fig.add_subplot(1, 3, 3)
    plot_pacf(diff_series, ax=ax3, lags=50, title="Partial Autocorrelation")
    ax3.axhline(y=-1.96 / np.sqrt(len(diff_series)), linestyle='--', color='gray')
    ax3.axhline(y=1.96 / np.sqrt(len(diff_series)), linestyle='--', color='gray')
    ax3.set_xlabel('Lags')

    plt.tight_layout()
    plt.show()

    # ADF Test to check Stationarity
    adf_result = adfuller(diff_series, autolag='AIC')
    print(f'ADF Statistic: {adf_result[0]}')
    print(f'p-value: {adf_result[1]}')
    for key, value in adf_result[4].items():
        print(f'Critical Value ({key}): {value}')
    if adf_result[1] < 0.05:
        print('Series is stationary according to ADF test.')
    else:
        print('Series is not stationary according to ADF test.')

    # KPSS Test
    kpss_result = kpss(diff_series, nlags='auto')
    print("KPSS Test Statistic:", kpss_result[0])
    print("p-value:", kpss_result[1])
    for key, value in kpss_result[3].items():
        print(f'Critical Value ({key}): {value}')
    if kpss_result[1] < 0.05:
        print('Evidence suggests the series is not stationary according to KPSS test.')
    else:
        print('No evidence against the null hypothesis; the series is stationary according to KPSS test.')

    return diff_series


# Example usage
transformation(data['Rate'])

# Finding Optimal Parameters using Time Series Split
tscv = TimeSeriesSplit(n_splits=5)

p = range(0, 3)
q = range(0, 7)
d = 1

# Generate all possible combinations of p, d, and q (with d fixed at 1)
pdq = list(itertools.product(p, [d], q))

best_aic_tss = float('inf')
best_params_tss = None

for param in pdq:
    try:
        aic_values = []
        for train_index, test_index in tscv.split(data):
            train_data_tss, test_data_tss = data.iloc[train_index], data.iloc[test_index]
            mod = sm.tsa.ARIMA(train_data_tss['Rate'], order=param, enforce_stationarity=False,
                               enforce_invertibility=False)
            results = mod.fit()
            aic_values.append(results.aic)

        mean_aic = np.mean(aic_values)
        if mean_aic < best_aic_tss:
            best_aic_tss = mean_aic
            best_params_tss = param

    except Exception as e:
        continue

print(f'Best AIC (TimeSeriesSplit): {best_aic_tss}')
print(f'Best Parameters (TimeSeriesSplit): {best_params_tss}')

# Bai-Perron test for Structural Breakpoints
# Convert index to integer for analysis
data['Date'] = range(len(data))

# Detection
algo = rpt.Pelt(model="l1").fit(data['Rate'].values)
result = algo.predict(pen=10)

# Display results
rpt.display(data['Rate'].values, result)
plt.show()

# Print change points
print("Change points detected at indices:", result)

change_points = [15, 20, 30, 45, 50, 60, 85, 95, 125, 190, 205, 235, 270, 295, 300, 315, 323]

# Filter out any indices that are out of bounds for the DataFrame's size
change_points = [cp for cp in change_points if cp < len(data)]

# Plot the time series
plt.figure(figsize=(14, 7))
plt.plot(data.index, data['Rate'], label='Rate')

# Mark each change point with a vertical line
for cp in change_points:
    plt.axvline(x=data.index[cp], color='r', linestyle='--', label='Change Point' if cp == change_points[0] else "")

# Adding legend only once for Change Point
plt.legend()
plt.title('Time Series with Detected Change Points')
plt.show()

# Retrieve the dates corresponding to these indices
break_dates = data.index[change_points]
print("Dates of detected structural breaks:")
print(break_dates)

# Segment the data based on breaks
segments = np.split(data['Rate'].values, change_points)

# Define structural breakpoints
break_dates = ['1998-04-01', '1998-09-01', '1999-07-01', '2000-10-01',
               '2001-03-01', '2002-01-01', '2004-02-01', '2004-12-01',
               '2007-06-01', '2012-11-01', '2014-02-01', '2016-08-01',
               '2019-07-01', '2021-08-01', '2022-01-01', '2023-04-01',
               '2023-12-01']  # Example breakpoints

# Create dummy variables for structural breaks
for i, break_date in enumerate(break_dates):
    data[f'break_{i + 1}'] = (data.index >= break_date).astype(int)

# Display the first few rows to check the dummy variables
print(data.head())

# Define exogenous variables (dummy variables)
exog = data[[f'break_{i + 1}' for i in range(len(break_dates))]]

# Fit the ARIMAX model
model_arimax = sm.tsa.ARIMA(data['Rate'], order=best_params_tss, exog=exog)
results_arimax = model_arimax.fit()
print(results_arimax.summary())

# Forecast future values with ARIMAX
forecast_steps = 6
exog_forecast = np.tile([1] * len(break_dates), (forecast_steps, 1))  # Future values for dummy variables
forecast_arimax = results_arimax.get_forecast(steps=forecast_steps, exog=exog_forecast)
forecast_arimax_values = forecast_arimax.predicted_mean
print("ARIMAX Forecasted Values:")
print(forecast_arimax_values)

# Plot the ARIMAX forecast
plt.figure(figsize=(12, 6))
plt.plot(data.index, data['Rate'], label='Observed')
plt.plot(forecast_arimax_values.index, forecast_arimax_values, label='ARIMAX Forecast')
plt.fill_between(forecast_arimax.conf_int().index,
                 forecast_arimax.conf_int().iloc[:, 0],
                 forecast_arimax.conf_int().iloc[:, 1], color='k', alpha=.15)
plt.legend()
plt.show()

# Compute residuals
residuals_arimax = results_arimax.resid

# Calculate performance metrics for ARIMAX
mse_arimax = mean_squared_error(data['Rate'], results_arimax.fittedvalues)
mae_arimax = mean_absolute_error(data['Rate'], results_arimax.fittedvalues)
rmse_arimax = np.sqrt(mse_arimax)
mape_arimax = np.mean(np.abs(residuals_arimax / data['Rate'])) * 100
r2_arimax = r2_score(data['Rate'], results_arimax.fittedvalues)

# Print performance metrics for ARIMAX
print(f'ARIMAX Performance Metrics:')
print(f'MSE: {mse_arimax}')
print(f'MAE: {mae_arimax}')
print(f'RMSE: {rmse_arimax}')
print(f'MAPE: {mape_arimax}')
print(f'R2: {r2_arimax}')

# Time Series Split
tscv = TimeSeriesSplit(n_splits=5)

# Initialize variables to store the best parameters and minimum AIC
best_aic = float('inf')
best_params = None

# Define the range of p, d, and q values for ARIMA parameters
p = range(0, 3)
q = range(0, 7)
d = 1
pdq = list(itertools.product(p, [d], q))

# Loop through all combinations of parameters
for param in pdq:
    try:
        aic_values = []
        for train_index, test_index in tscv.split(data):
            train_data, test_data = data.iloc[train_index], data.iloc[test_index]
            mod = sm.tsa.ARIMA(train_data['Rate'], order=param, enforce_stationarity=False, enforce_invertibility=False)
            results = mod.fit()
            aic_values.append(results.aic)

        mean_aic = np.mean(aic_values)
        if mean_aic < best_aic:
            best_aic = mean_aic
            best_params = param

    except Exception as e:
        continue

print(f'Best AIC: {best_aic}')
print(f'Best Parameters: {best_params}')

data['index'] = range(len(data))
algo = rpt.Pelt(model="l1").fit(data['Rate'].values)
result = algo.predict(pen=10)

rpt.display(data['Rate'].values, result)
plt.show()

change_points = [cp for cp in result if cp < len(data)]
break_dates = data.index[change_points]
print("Dates of detected structural breaks:", break_dates)

for i, break_date in enumerate(break_dates):
    data[f'break_{i + 1}'] = (data.index >= break_date).astype(int)
exog = data[[f'break_{i + 1}' for i in range(len(break_dates))]]

model_arimax = sm.tsa.ARIMA(data['Rate'], order=best_params, exog=exog)
results_arimax = model_arimax.fit()
print(results_arimax.summary())

forecast_steps = 6
exog_forecast = np.tile([1] * len(break_dates), (forecast_steps, 1))
forecast_arimax = results_arimax.get_forecast(steps=forecast_steps, exog=exog_forecast)
forecast_arimax_values = forecast_arimax.predicted_mean
print("ARIMAX Forecasted Values:")
print(forecast_arimax_values)

plt.figure(figsize=(12, 6))
plt.plot(data.index, data['Rate'], label='Observed')
plt.plot(forecast_arimax_values.index, forecast_arimax_values, label='ARIMAX Forecast')
plt.fill_between(forecast_arimax.conf_int().index, forecast_arimax.conf_int().iloc[:, 0],
                 forecast_arimax.conf_int().iloc[:, 1], color='k', alpha=.15)
plt.legend()
plt.show()

residuals_arimax = results_arimax.resid

mse_arimax = mean_squared_error(data['Rate'], results_arimax.fittedvalues)
mae_arimax = mean_absolute_error(data['Rate'], results_arimax.fittedvalues)
rmse_arimax = np.sqrt(mse_arimax)
mape_arimax = np.mean(np.abs(residuals_arimax / data['Rate'])) * 100
r2_arimax = r2_score(data['Rate'], results_arimax.fittedvalues)

print(f'ARIMAX Performance Metrics:')
print(f'MSE: {mse_arimax}')
print(f'MAE: {mae_arimax}')
print(f'RMSE: {rmse_arimax}')
print(f'MAPE: {mape_arimax}')
print(f'R2: {r2_arimax}')
