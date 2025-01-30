from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))

params["adaptive_infrastructure"]= False

params["version_num"] = 'Sensitivity_all_coordination_NS_29Jan25'
params["seasonal_regulation"] = True
params["sensitivity_analysis"] = True
params["update_figures"] = False


projection_multipliers = np.linspace(0.8, 1.1, 31)

for i, mult in enumerate(projection_multipliers):
    mult = round(mult, 2)
    params["projection_multiplier"] = mult
    
    
    # No coordination
    params['Constraint_tag'] = 'No_coordination'

    ## Optimize for infrastructure
    params["joint_infrastructure"]= False
    ## Assume that there is no trading market
    params["trading_market"] = False                     

    ## Sensitivity 
    params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
    params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

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

    # year when market is established
    ## save the capex file path to read the capex results
    params['figpath_capex'] = params['figpath']  

    params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
    params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

    if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

    m = capacity_expansion(params)
    m.main()

    print("completed partial coordination optimization for run = {}".format(i))


    # Full coordination
    params['Constraint_tag'] = 'Full_coordination'

    # Allow for only trading markets
    
    params["joint_infrastructure"]= True
    params["trading_market"] = True                 

    params['figpath'] = 'Figures/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
    params['figpath_base'] = 'Figures/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

    if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])

    m = capacity_expansion(params)
    m.main()

    print("completed full coordination optimization for run = {}".format(i))

    
    print("completed all optimization for run = {}".format(i))