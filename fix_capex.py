from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

params["version_num"] = 'only_operation_13Nov24'
params["seasonal_regulation"] = False
params["sensitivity_analysis"] = False
params["update_figures"] = True
params["only_opex_trading"]= False

params["Constraint_tag"] = "Individual"


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


# Operating cost only


params["only_opex_trading"]= True


## save the capex file path to read the capex results
params['figpath_capex'] = params['figpath']    
params["Constraint_tag"] = "Subembayment"

## create new figure path for opex optimization
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "opex_opt/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "opex_opt_" 

if not os.path.exists(params['figpath']):
    os.makedirs(params['figpath'])

m = capacity_expansion(params)

m.main()

print("completed opex optimization run")


# Capital + Operating cost optimization


params["only_opex_trading"]= False 
params["Constraint_tag"] = "Subembayment"

## create new figure path for capex_opex optimization
params['figpath'] = 'Figures/' + params['version_num'] +  "/" + file_tag + "capex_opex_opt/" 
params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + file_tag + "capex_opex_opt_" 

if not os.path.exists(params['figpath']):
    os.makedirs(params['figpath'])

m = capacity_expansion(params)

m.main()

print("completed capex and opex optimization run")


