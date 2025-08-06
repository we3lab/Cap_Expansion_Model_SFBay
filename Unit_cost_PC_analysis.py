from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

# Script that calculates the unit costs for S-PC case

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath) 
params = json.load(open(fp))

# Initialize parameters 
## set unit cost analysis to True
params["version_num"] = 'Unit_cost_by_WWTP'
params["unit_cost_analysis"] = True

# Set unit cost times to calculate as June 2036, June 2045, and June 2054
unit_cost_times = ['2036-06-01', '2045-06-01', '2054-06-01']

## Define seasonal regulations
params["seasonal_regulation"] = True


## Staged infrastructure
params["staged_infrastructure"]= True
params["trading_market_year"] = 0
params["unfix_infrastructure_year"] = 0  

## Set other constraints
params["sensitivity_analysis"] = False
params["update_figures"] = False




for i, dt in enumerate(unit_cost_times):
    
    params["unit_cost_dt"] = dt
    

    # No coordination
    params['Constraint_tag'] = 'No_coordination'

    ## Optimize for infrastructure
    params["joint_infrastructure"]= False
    ## Assume that there is no trading market
    params["trading_market"] = False                     

    ## Sensitivity 
    params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  
    params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_"

    if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

    m = capacity_expansion(params)
    m.main()

    print("completed no coordination optimization for run = {}".format(i))



    # Partial coordination
    params['Constraint_tag'] = 'Partial_coordination'

    # Allow for only trading markets
    
    params["joint_infrastructure"]= False
    params["trading_market"] = True      
    params["trading_market_year"] = 0
    params["unfix_infrastructure_year"] = 0           

    # year when market is established
    ## save the capex file path to read the capex results
    params['figpath_capex'] = params['figpath']  

    params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/" 
    params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_"

    if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

    m = capacity_expansion(params)
    m.main()

    print("completed partial coordination optimization for run = {}".format(i))

    
    print("completed all optimization for run = {}".format(i))