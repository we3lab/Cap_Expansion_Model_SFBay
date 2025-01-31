from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath) 
params = json.load(open(fp))

year = 29

# Initialize parameters
params["version_num"] = 'Adaptive_' + str(year) + 'yr_30Jan25'

# assume trading market and joint infrastructure starts in year 10
params["trading_market_year"] = year
params["unfix_infrastructure_year"] = year

# Adaptive infrastructure
params["adaptive_infrastructure"]= True

# Set other parameters
params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False



# Case 2: Staged, not coordinated
params["update_figures"] = False
params["Constraint_tag"] = 'No_coordination'
    ## Assume no joint_infrastructure
params["joint_infrastructure"]= False
    ## Assume that there is no trading market
params["trading_market"] = False 

params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params["Constraint_tag"] + "_"

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
#m.main()

print("completed adaptive and not coordinated optimization for run")

# Case 4: Staged, partially coordinated
#'''
params["update_figures"] = False
params['Constraint_tag'] = 'Partial_coordination'

    ## Allow for only trading markets
params["joint_infrastructure"]= False
params["trading_market"] = True                 


    ## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']  
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()

print("completed adaptive and partially coordinated optimization for run")
#'''

'''
# Case 6: Staged, fully coordinated
params['Constraint_tag'] = 'Full_coordination'
params["update_figures"] = True

    ## Allow for only trading markets
params["joint_infrastructure"]= True
params["trading_market"] = True                 


    ## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']  

params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params["Constraint_tag"] + "/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params["Constraint_tag"] + "_" 

if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

m = capacity_expansion(params)
m.main()

print("completed adaptive and fully coordinated optimization for run")
'''
