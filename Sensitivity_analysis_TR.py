from CapExpModel import capacity_expansion
import os, json
import numpy as np
import os

# Script that runs sensitivity analysis for all coordination cases as a function of discharge multipliers

basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
fp = os.path.join(os.getcwd(),basepath)     
params = json.load(open(fp))


params["seasonal_regulation"] = True
params["sensitivity_analysis"] = True
params["update_figures"] = False
params["unit_cost_analysis"] = False

projection_multipliers = np.arange(1.0, 3.1, 0.5)


for staged_scenario in ["Non_Staged", "Staged"]:
    if staged_scenario == "Non_Staged":
        params["staged_infrastructure"]= False
        params["version_num"] = 'Sensitivity_all_coordination_NS_TR'
    
    elif staged_scenario == "Staged":
        params["staged_infrastructure"]= True
        params["version_num"] = 'Sensitivity_all_coordination_S_TR'
    
    for i, mult in enumerate(projection_multipliers):
        mult = round(mult, 2)
        params["TR"] = mult
        
        # No coordination
        params['Constraint_tag'] = 'No_coordination'

        ## Optimize for infrastructure
        params["joint_infrastructure"]= False
        ## Assume that there is no trading market
        params["trading_market"] = False                     

        ## Sensitivity 
        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

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

        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

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
        params["trading_market_year"] = 0
        params["unfix_infrastructure_year"] = 0                   

        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

        if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])

        m = capacity_expansion(params)
        m.main()

        print("completed full coordination optimization for run = {}".format(i))


        # Full coordination, Market Year 10
        year = 10
        params['Constraint_tag'] =  'Full_' + str(year) + 'yr_coordination'

        # Allow for only trading markets
        
        params["joint_infrastructure"]= True
        params["trading_market"] = True    
        params["trading_market_year"] = year
        params["unfix_infrastructure_year"] = year             

        params['figpath'] = 'Results/' + params['version_num'] +  "/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
        params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] +  "_" + str(mult) + "_" 

        if not os.path.exists(params['figpath']):
            os.makedirs(params['figpath'])

        m = capacity_expansion(params)
        m.main()

        print("completed full coordination optimization for run = {}".format(i))

        
        print("completed all optimization for run = {}".format(i))