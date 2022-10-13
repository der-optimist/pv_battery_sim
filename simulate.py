import pandas as pd
import time
import matplotlib.pyplot as plt

#############
### Input ###
#############

# Specify Infput Files
csvPv = '2022-10-06-11-39_pv_ac.csv'
csvDemand = '2022-10-06-11-39_verbrauch.csv'

# Specify Batteries
batteryHVS05p1 = {'batteryName': 'HVS 5.1',
                  'batteryCapacity': 5.1,
                  'quotaUsable': 0.9,
                  'maxPowerStore': 4510,
                  'maxPowerUse': 4510,
                  'priceBattery': 5000,
                  'batteryEfficiencyStore': 0.97,
                  'batteryEfficiencyUse': 0.97}
batteryHVS07p7 = {'batteryName': 'HVS 7.7',
                  'batteryCapacity': 7.7,
                  'quotaUsable': 0.9,
                  'maxPowerStore': 6760,
                  'maxPowerUse': 6760,
                  'priceBattery': 6500,
                  'batteryEfficiencyStore': 0.97,
                  'batteryEfficiencyUse': 0.97}
batteryHVS10p2 = {'batteryName': 'HVS 10.2',
                  'batteryCapacity': 10.2,
                  'quotaUsable': 0.9,
                  'maxPowerStore': 9010,
                  'maxPowerUse': 9010,
                  'priceBattery': 9000,
                  'batteryEfficiencyStore': 0.97,
                  'batteryEfficiencyUse': 0.97}
batteryHVM11p0 = {'batteryName': 'HVM 11.0',
                  'batteryCapacity': 11,
                  'quotaUsable': 0.9,
                  'maxPowerStore': 4510,
                  'maxPowerUse': 4510,
                  'priceBattery': 9500,
                  'batteryEfficiencyStore': 0.96,
                  'batteryEfficiencyUse': 0.96}
batteryHVM13p8 = {'batteryName': 'HVM 13.8',
                  'batteryCapacity': 13.8,
                  'quotaUsable': 0.9,
                  'maxPowerStore': 5630,
                  'maxPowerUse': 5630,
                  'priceBattery': 11000,
                  'batteryEfficiencyStore': 0.96,
                  'batteryEfficiencyUse': 0.96}
batteryHVM16p6 = {'batteryName': 'HVM 16.6',
                  'batteryCapacity': 16.6,
                  'quotaUsable': 0.9,
                  'maxPowerStore': 6760,
                  'maxPowerUse': 6760,
                  'priceBattery': 15000,
                  'batteryEfficiencyStore': 0.96,
                  'batteryEfficiencyUse': 0.96}
batteryHVM19p3 = {'batteryName': 'HVM 19.3',
                  'batteryCapacity': 19.3,
                  'quotaUsable': 0.9,
                  'maxPowerStore': 7880,
                  'maxPowerUse': 7880,
                  'priceBattery': 18000,
                  'batteryEfficiencyStore': 0.96,
                  'batteryEfficiencyUse': 0.96}
batteryHVM22p1 = {'batteryName': 'HVM 22.1',
                  'batteryCapacity': 22.1,
                  'quotaUsable': 0.9,
                  'maxPowerStore': 9010,
                  'maxPowerUse': 9010,
                  'priceBattery': 20000,
                  'batteryEfficiencyStore': 0.96,
                  'batteryEfficiencyUse': 0.96}
batteryList = [batteryHVS05p1, batteryHVS07p7, batteryHVS10p2, batteryHVM11p0, batteryHVM13p8, batteryHVM16p6, batteryHVM19p3, batteryHVM22p1]

# Energy Cost and Refund
costKwh = 0.28 # €/kWh
refundKwh = 0.077 # €/kWh

printSoc = True
debug = False

#################
### End Input ###
#################

t = time.time()


# read csv files
demandSeries = pd.read_csv(csvDemand, index_col=0, header=0, parse_dates=True, squeeze=True)
pvSeries = pd.read_csv(csvPv, index_col=0, header=0, parse_dates=True, squeeze=True)
dataInput = pd.merge_ordered(demandSeries, pvSeries, how="outer", left_on="time", right_on="time", fill_method="ffill").dropna().reset_index(drop=True)
dataInput['validTime'] = (dataInput['time'].shift(-1)-dataInput['time']).fillna(pd.Timedelta(seconds=0))
dataInput.drop(dataInput.tail(1).index,inplace=True)
dataOutput = pd.DataFrame(columns = ['time', 'energyInBatteryKwh', 'socPercent', 'energyFromNetTotalKwh', 'energyToNetTotalKwh', 'energyToBatteryTotalKwh', 'energyFromBatteryTotalKwh', 'CostNetWithoutBattery', 'CostNetWithBattery', 'RefundNetWithoutBattery', 'RefundNetWithBattery', 'CostSavingBattery'], index=range(dataInput.shape[0]))

if debug:
    print('Import took {:.2f} seconds'.format(time.time()-t))
t = time.time()

for battery in batteryList:
    batteryName = battery['batteryName']
    batteryCapacity = battery['batteryCapacity']
    quotaUsable = battery['quotaUsable']
    maxPowerStore = battery['maxPowerStore']
    maxPowerUse = battery['maxPowerUse']
    priceBattery = battery['priceBattery']
    batteryEfficiencyStore = battery['batteryEfficiencyStore']
    batteryEfficiencyUse = battery['batteryEfficiencyUse']
    
    # Specify and convert initial values
    batteryCapacityWs = quotaUsable * batteryCapacity * 3600000
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
    
    for index, row in dataInput.iterrows():
        ts = row['time']
        powerPv = row['sensor.el_leistung_pv_ac.value']
        if powerPv < 0:
            powerPv = 0
        powerDemand = row['sensor.el_leistung_verbrauch_gesamt.value']
        if powerDemand < 0:
            powerDemand = 0
        validTimeSeconds = row['validTime'].total_seconds()
        
        if (index % 10000) == 0 and debug:
            print('{} - {}'.format(batteryName,ts))
        
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
    
    if debug:
        print('Calculation took {:.2f} seconds'.format(time.time()-t))
        print('')
    
    tsStart = dataOutput.loc[0]['time']
    tsEnd = dataOutput.loc[dataInput.shape[0]-1]['time']
    simulationDurationYears = (tsEnd - tsStart).total_seconds() / 31536000
    costSavingPerYear = CostSavingBattery / simulationDurationYears
    amortisationYears = priceBattery / costSavingPerYear
    
    print('###################')
    print('# {} #'.format(batteryName))
    print('###################')
    print('Saving calculated: {:.2f}'.format(CostSavingBattery))
    print('Years calculated: {:.2f}'.format(simulationDurationYears))
    print('Saving per Year: {:.2f}'.format(costSavingPerYear))
    print('Amotisation: {:.1f} Years'.format(amortisationYears))
    print('Load Cycles calculated: {:.2f}'.format(((energyToBatteryTotalWs / 3600000)/(quotaUsable * batteryCapacity))))
    print('Load Cycles until Amotisation: {:.1f}'.format(((energyToBatteryTotalWs / 3600000)/(quotaUsable * batteryCapacity))*(amortisationYears/simulationDurationYears)))
    print('###################')
    
    if printSoc:
        pd.plotting.register_matplotlib_converters()
        plt.rcParams["figure.figsize"] = (50,5)
        fig, ax = plt.subplots()
        ax.plot(dataOutput.time ,dataOutput.socPercent, label='SoC - {}'.format(batteryName))
        ax.legend(loc="lower left")
        plt.xlim([tsStart, tsEnd])
        ax.grid()
    
    print('')
    print('')
