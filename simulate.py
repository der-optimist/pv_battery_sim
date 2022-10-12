import pandas as pd
import time
import matplotlib.pyplot as plt

#############
### Input ###
#############

# Specify Infput Files
csvPv = '2022-10-06-11-39_pv_ac.csv'
csvDemand = '2022-10-06-11-39_verbrauch.csv'

# Specify Power, Capacity and Price
batteryCapacity = 11 # kWh
maxPowerStore = 4510 # W - HVM 11
#maxPowerStore = 5630 # W - HVM 13.8
#maxPowerStore = 6760 # W - HVM 16.6
#maxPowerStore = 7880 # W - HVM 19.3
#maxPowerStore = 9010 # W - HVM 22.1
#maxPowerStore = 4510 # W - HVS 5.1
#maxPowerStore = 6760 # W - HVS 7.7
#maxPowerStore = 9010 # W - HVS 10.2
maxPowerUse = maxPowerStore
priceBattery = 10000

# Specify Efficiency
batteryEfficiencyStore = 0.97
batteryEfficiencyUse = 0.97
inverterEfficiency = 0.98

# Energy Cost and Refund
costKwh = 0.28 # €/kWh
refundKwh = 0.077 # €/kWh

#################
### End Input ###
#################

t = time.time()

# Specify and convert initial values
batteryCapacityWs = batteryCapacity * 3600000
energyInBatteryWs = 0.5 * batteryCapacityWs
energyFromNetTotalWs = 0
energyToNetTotalWs = 0
energyToBatteryTotalWs = 0
energyFromBatteryTotalWs = 0
costWs = costKwh / 3600000
refundWs = refundKwh / 3600000
CostNetWithoutBattery = 0
CostNetWithBattery = 0
RefundNetWithoutBattery = 0
RefundNetWithBattery = 0

# read csv files
demandSeries = pd.read_csv(csvDemand, index_col=0, header=0, parse_dates=True, squeeze=True)
pvSeries = pd.read_csv(csvPv, index_col=0, header=0, parse_dates=True, squeeze=True)
dataInput = pd.merge_ordered(demandSeries, pvSeries, how="outer", left_on="time", right_on="time", fill_method="ffill").dropna().reset_index(drop=True)
dataInput['validTime'] = (dataInput['time'].shift(-1)-dataInput['time']).fillna(pd.Timedelta(seconds=0))
dataInput.drop(dataInput.tail(1).index,inplace=True)
dataOutput = pd.DataFrame(columns = ['time', 'energyInBatteryKwh', 'socPercent', 'energyFromNetTotalKwh', 'energyToNetTotalKwh', 'energyToBatteryTotalKwh', 'energyFromBatteryTotalKwh', 'CostNetWithoutBattery', 'CostNetWithBattery', 'RefundNetWithoutBattery', 'RefundNetWithBattery', 'CostSavingBattery'], index=range(dataInput.shape[0]))


print('Import dauerte {}'.format(time.time()-t))
t = time.time()

for index, row in dataInput.iterrows():
    ts = row['time']
    powerPv = row['sensor.el_leistung_pv_ac.value']
    if powerPv < 0:
        powerPv = 0
    powerDemand = row['sensor.el_leistung_verbrauch_gesamt.value']
    if powerDemand < 0:
        powerDemand = 0
    validTimeSeconds = row['validTime'].total_seconds()
    
    if (index % 1000) == 0:
        print(ts)
    
    if powerPv > powerDemand:
        energySurplus = (powerPv - powerDemand) * validTimeSeconds
        if (powerPv - powerDemand) > maxPowerStore:
            powerAvailableForStoring = maxPowerStore
        else:
            powerAvailableForStoring = (powerPv - powerDemand)
        energyAvailableForStoring = powerAvailableForStoring * validTimeSeconds
        if energyAvailableForStoring > (batteryCapacityWs - energyInBatteryWs):
            energyToStore = (batteryCapacityWs - energyInBatteryWs)
        else:
            energyToStore = energyAvailableForStoring
        energyToNet = energySurplus - energyToStore
        energyInBatteryWs = energyInBatteryWs + (batteryEfficiencyStore * energyToStore)
        energyToNetTotalWs = energyToNetTotalWs + energyToNet
        energyToBatteryTotalWs = energyToBatteryTotalWs + (batteryEfficiencyStore * energyToStore)
        RefundNetWithBattery = RefundNetWithBattery + (energyToNet * refundWs)
        RefundNetWithoutBattery = RefundNetWithoutBattery + ((energyToNet + energyToStore) * refundWs)
        CostSavingBattery = (CostNetWithoutBattery - RefundNetWithoutBattery) - (CostNetWithBattery - RefundNetWithBattery)
        
        rowOutput = {'time': ts, 
                     'energyInBatteryKwh': (energyInBatteryWs / 3600000), 
                     'socPercent': (100 * energyInBatteryWs / batteryCapacityWs),
                     'energyFromNetTotalKwh': (energyFromNetTotalWs / 3600000),
                     'energyToNetTotalKwh': (energyToNetTotalWs / 3600000),
                     'energyToBatteryTotalKwh': (energyToBatteryTotalWs / 3600000),
                     'energyFromBatteryTotalKwh':(energyFromBatteryTotalWs / 3600000),
                     'CostNetWithoutBattery': CostNetWithoutBattery,
                     'CostNetWithBattery': CostNetWithBattery,
                     'RefundNetWithoutBattery': RefundNetWithoutBattery,
                     'RefundNetWithBattery': RefundNetWithBattery,
                     'CostSavingBattery': CostSavingBattery}
        dataOutput.loc[index] = rowOutput
        
    else:
        powerDemandFromBatteryOrNet = powerDemand - powerPv
        energyDemandFromBatteryOrNet = powerDemandFromBatteryOrNet * validTimeSeconds
        if powerDemandFromBatteryOrNet > maxPowerUse:
            powerRequestFromBattery = maxPowerUse
        else:
            powerRequestFromBattery = powerDemandFromBatteryOrNet
        energyRequestFromBattery = powerRequestFromBattery * validTimeSeconds
        if energyRequestFromBattery > (energyInBatteryWs * batteryEfficiencyUse):
            energyFromBattery = (energyInBatteryWs * batteryEfficiencyUse)
        else:
            energyFromBattery = energyRequestFromBattery
        energyFromNet = energyDemandFromBatteryOrNet - energyFromBattery
        energyInBatteryWs = energyInBatteryWs - (energyFromBattery / batteryEfficiencyUse)
        energyFromNetTotalWs = energyFromNetTotalWs + energyFromNet
        energyFromBatteryTotalWs = energyFromBatteryTotalWs + energyFromBattery
        CostNetWithBattery = CostNetWithBattery + (energyFromNet * costWs)
        CostNetWithoutBattery = CostNetWithoutBattery + (energyDemandFromBatteryOrNet * costWs)
        CostSavingBattery = (CostNetWithoutBattery - RefundNetWithoutBattery) - (CostNetWithBattery - RefundNetWithBattery)
        
        rowOutput = {'time': ts, 
                     'energyInBatteryKwh': (energyInBatteryWs / 3600000), 
                     'socPercent': (100 * energyInBatteryWs / batteryCapacityWs),
                     'energyFromNetTotalKwh': (energyFromNetTotalWs / 3600000),
                     'energyToNetTotalKwh': (energyToNetTotalWs / 3600000),
                     'energyToBatteryTotalKwh': (energyToBatteryTotalWs / 3600000),
                     'energyFromBatteryTotalKwh':(energyFromBatteryTotalWs / 3600000),
                     'CostNetWithoutBattery': CostNetWithoutBattery,
                     'CostNetWithBattery': CostNetWithBattery,
                     'RefundNetWithoutBattery': RefundNetWithoutBattery,
                     'RefundNetWithBattery': RefundNetWithBattery,
                     'CostSavingBattery': CostSavingBattery}
        dataOutput.loc[index] = rowOutput
        
print('Berechnen dauerte {}'.format(time.time()-t))

tsStart = dataOutput.loc[0]['time']
tsEnd = dataOutput.loc[dataInput.shape[0]-1]['time']
simulationDurationYears = (tsEnd - tsStart).total_seconds() / 31536000
costSavingPerYear = CostSavingBattery / simulationDurationYears
amortisationYears = priceBattery / costSavingPerYear

print('Saving: {:.2f}, Jahre: {:.2f}, Saving pro Jahr: {:.2f}, Amotisation: {:.1f} Jahre'.format(CostSavingBattery, simulationDurationYears, costSavingPerYear, amortisationYears))

plt.rcParams["figure.figsize"] = (15,5)
fig, ax = plt.subplots()
ax.plot(dataOutput.time ,dataOutput.socPercent, label='SoC')
ax.legend()
plt.xlim([tsStart, tsEnd])
ax.grid()

