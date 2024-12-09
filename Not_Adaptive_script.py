from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

# Initialize parameters
params["version_num"] = 'Not_adaptive_06Dec24'
params["seasonal_regulation"] = True
params["sensitivity_analysis"] = False
params["update_figures"] = False
    # Not adaptive infrastructure
params["adaptive_infrastructure"]= False



# Case 1: Not adaptive, not coordinated
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
m.main()

print("completed not adaptive and not coordinated optimization for run")



# Case 3: Not adaptive, partially coordinated
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

print("completed not adaptive and partially coordinated optimization for run")


# Case 5: Not adaptive, fully coordinated
params['Constraint_tag'] = 'Full_coordination'

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

print("completed not adaptive and fully coordinated optimization for run")