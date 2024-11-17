from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

params["version_num"] = 'Trading_market_start_year_16Nov24'
params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False
params["update_figures"] = False

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




# Establish trading market at a certain year
# Allow for both joint-infrastructure and trading 

params["joint_infrastructure"]= True
params["unfix_infrastructure_year"] = 0          # Year when joint_infrastructure planning can start
params["trading_market"] = True                  # true if trading market is allowed
params["trading_market_year"] = 31                # Year when trading_market is allowed


## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']    



## create new figure path for opex optimization
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "opex_opt/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "opex_opt_" 

if not os.path.exists(params['figpath']):
    os.makedirs(params['figpath'])

m = capacity_expansion(params)

m.main()

print("completed opex optimization run")


# Capital + Operating cost optimization
'''

params["joint_infrastructure"]= False 
params["Constraint_tag"] = "Subembayment"

## create new figure path for capex_opex optimization
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "capex_opex_opt/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "capex_opex_opt_" 

if not os.path.exists(params['figpath']):
    os.makedirs(params['figpath'])

m = capacity_expansion(params)

m.main()

print("completed capex and opex optimization run")
'''

