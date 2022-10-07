import pandas as pd

demand = pd.read_csv('2022-10-06-11-39_verbrauch_test.csv', index_col=0, header=0, parse_dates=True, squeeze=True)
pv = pd.read_csv('2022-10-06-11-39_pv_ac_test.csv', index_col=0, header=0, parse_dates=True, squeeze=True)

BatteryCapacity = 11 # kWh
BatteryEfficiencyStore = 0.95
BatteryEfficiencyUse = 0.95
MaxPowerStore = 4.5 # kW
MaxPowerUse = 4.5 # kW
InverterEfficiency = 0.95

data = pd.merge_ordered(demand, pv, how="outer", left_on="time", right_on="time", fill_method="ffill").dropna().reset_index(drop=True)
data['delta'] = (data['time'].shift(-1)-data['time']).fillna(pd.Timedelta(seconds=0))
data.drop(data.tail(1).index,inplace=True)
