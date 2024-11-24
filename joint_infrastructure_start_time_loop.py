from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

params["version_num"] = 'Joint_infrastructure_loop_over_23Nov24'
params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False
params["update_figures"] = False
params["Constraint_tag"] = 'No_coordination'

# Optimize for infrastructure
params["joint_infrastructure"]= False

# Assume that there is no trading market
params["trading_market"] = False                     # true if trading market is allowed

# Sensitivity 
params["projection_multiplier"] = 1.0

if params["seasonal_regulation"]:
    file_tag = "Seasonal/"
else:
    file_tag = "Year_round/"

params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "capex_opt/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "capex_opt_" 

if not os.path.exists(params['figpath']):
    os.makedirs(params['figpath'])

m = capacity_expansion(params)

m.main()

print("completed capex optimization run")




# Market is always allowed
# Joint-infrastructure is allowed to start at different years

# Allow for both joint-infrastructure and trading 

params["joint_infrastructure"]= True
params["trading_market_year"] = 0          # Year when joint_infrastructure planning can start
params["trading_market"] = True                  # true if trading market is allowed
params["Constraint_tag"] = 'Full_coordination'

# year when market is established
## if trading_market_year = 0; then nutrient credits can be traded at time = 0
## if trading_market_year = 30; then nutrient credits cannot be traded for the duration of the simulation
years = np.linspace(0,30,31).astype(np.int64)

## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']  

# loop over all years
for year in years:
    params["unfix_infrastructure_year"] = year

    ## create new figure path for opex optimization
    params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "opex_opt/" + str(year) + "/" 
    params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "opex_opt_"  + str(year) + "_" 

    if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

    m = capacity_expansion(params)

    m.main()

    print('completed optimization run for joint-infrastructure planning established in year:', year)

print("completed opex optimization run for all years")