################################################
#
# This file contains an optimization model for
# capacity expansion of regional wastewater
# treatment plants in the SF Bay Area to meet
# nutrient discharge limits.
#
################################################



import numpy as np
import pandas as pd
import os, json, warnings
from pyomo.environ import *



class capacity_expansion():
    def __init__(self, params):
        for k, v in params.items():
            setattr(self, k, v)
        
        # set up time periods of model
        start_date = pd.to_datetime(self.start_date)
        self.datetime = pd.date_range(start=start_date, periods = 12*self.total_years, freq=self.timestep_freq)
        
        start_year = str(start_date.year)
        end_year = str(self.datetime[-1].year)
        self.datetime_years = pd.date_range(start=start_year, end = end_year, freq='YS')

    
    
    def main(self):
        """
        Run the model.
            - Select the solver
            -
            -
            -
        """
        model = self.build()

        output_path = self.figpath_base + 'solver_log.txt'
        
        # Solve MILP with gurobi
        if self.solver_type == 'gurobi' and self.capex_costing_power is None or not len(self.capex_costing_power) > 0:
            print('Using gurobi to solve the MILP')
            solver = SolverFactory('gurobi')
            solver.solve(model, tee=True, logfile=output_path)
        
        # Solve MILP with gurobi_direct
        elif self.solver_type == 'gurobi' and self.capex_costing_power is not None and len(self.capex_costing_power) > 0:
            print('Using gurobi direct to solve the MILP with power law capex costing')
            self.solver_type = 'gurobi_direct'
            #solver = SolverFactory('gurobi', solver_io='nl')
            solver = SolverFactory('gurobi_direct')
            solver.options['NonConvex'] = 2  # allows nonlinear/nonconvex terms
            solver.solve(model, tee=True, logfile=output_path)
        
        # Solve LP with ipopt
        elif self.solver_type == 'ipopt':
            solver = SolverFactory('ipopt')
            solver.solve(model, tee=True)
        
        
        # Solve with MindtPy
        elif self.solver_type == 'mindtpy':
            solver = SolverFactory('mindtpy')
            solver.solve(model, 
                        mip_solver = 'gurobi',
                        nlp_solver = 'ipopt',
                        tee=True)
        else:
            print('Solver not recognized. Please select either gurobi, ipopt, or mindtpy')
            return None

        model = self.print_results(model)

        # compute unit costs for partial coordination figure if required

        if self.unit_cost_analysis and self.Constraint_tag == 'Partial_coordination':
            
            print('Computing unit costs for partial coordination')
            model = self.compute_unit_costs_WWTP(model, solver)
        
        return model
    
    def print_results(self, model):
        print('Policy Scenario:', self.Constraint_tag)
        print('Staged Infrastructure:', self.staged_infrastructure)
        print('Projected Discharge Multiplier:', self.projection_multiplier)
        print('Solver:', self.solver_type)
        print('Total NPV Cost = ', round(model.total_cost(),2), 'million')
        
        for WWTP in model.WWTP:
            print('WWTP: ', WWTP, '(Total Cost:', round(model.total_cost_WWTP[WWTP](),2), 'million)')
            for L in model.L:
                if round(sum(model.u[WWTP,L,t].value for t in model.t)) == 1:
                    #print('\t',L+':', round(model.x_max[WWTP,L](),2),'; Lower bound (' + str(model.LB[WWTP, L].value)+ '); Capex:',round(model.capex_NPV[WWTP,L](),2), '; Opex:', round(model.opex_NPV[WWTP,L](),2))
                    print('\t',L+':', round(model.x_max[WWTP,L](),2), '(' + str(round(max(model.x[WWTP,L,t].value for t in model.t),1)) + ')',
                          '; Capex:',round(model.capex_NPV[WWTP,L](),2), '; Opex:', round(model.opex_NPV[WWTP,L](),2))
                    print(f'\t\t Max flow capacity: {round(model.x_flow_max[WWTP, L](),2)} mgd; Flow capacity used: {round(max(model.x_flow[WWTP,L,t].value for t in model.t),2)} mgd')
                else:
                    print('\t',L+': not built', round(model.capex_NPV[WWTP,L](),2))
        
        #print summary results
        summary = pd.DataFrame(index=model.WWTP)
        summary['Total_cost'] = [model.total_cost_WWTP[WWTP].value for WWTP in model.WWTP]
        summary['Total_capex'] = [sum(model.capex_NPV[WWTP,L].value for L in model.L) for WWTP in model.WWTP]
        summary['Total_opex'] = [sum(model.opex_NPV[WWTP,L].value for L in model.L) for WWTP in model.WWTP]
        summary['Max_capacity'] = [sum(sum(model.u[WWTP,L,t].value for t in model.t) * model.x_max[WWTP,L].value for L in model.L) - model.x_max[WWTP, 'L2'].value * sum(model.u[WWTP,'L2upg3',t].value for t in model.t) for WWTP in model.WWTP]
        summary['Max_flow_capacity'] = [sum(sum(model.u[WWTP,L,t].value for t in model.t) * model.x_flow_max[WWTP,L].value for L in model.L) - model.x_flow_max[WWTP, 'L2'].value * sum(model.u[WWTP,'L2upg3',t].value for t in model.t) for WWTP in model.WWTP]
        summary['Total_removal'] = [sum(model.r[WWTP,t].value for t in model.t) for WWTP in model.WWTP]
        for L in model.L:
            summary[L+'_capex_NPV'] = [model.capex_NPV[WWTP,L].value for WWTP in model.WWTP]
            summary[L+'_opex_NPV'] = [model.opex_NPV[WWTP,L].value for WWTP in model.WWTP]
            summary[L+'_x_max'] = [sum(model.u[WWTP,L,t].value for t in model.t) * model.x_max[WWTP,L].value for WWTP in model.WWTP]
            summary[L+'_x_flow_max'] = [sum(model.u[WWTP,L,t].value for t in model.t) * model.x_flow_max[WWTP,L].value for WWTP in model.WWTP]
            summary[L+'_removal'] = [sum(model.x[WWTP,L,t].value * model.status[WWTP,L,t].value for t in model.t) for WWTP in model.WWTP]

        summary.loc['Total'] = summary.sum()
        summary.to_csv(self.figpath_base +'summary.csv')

        self.summary = summary
        
        # print individual WWTP results
        for WWTP in model.WWTP:
            
            #print TIN removal results
            results = pd.DataFrame(index=self.datetime)
            results['Required_removal'] =[value(model.dis_minus_reg[WWTP,t]) for t in model.t]
            results['Total_removal'] = [model.r[WWTP,t].value for t in model.t]
            results['Excess_treatment'] = [model.excess_removal[WWTP,t].value for t in model.t]
            results['Status_buying'] = [model.status_buying[WWTP,t].value for t in model.t]
            for L in model.L:                
                results[L+'_r'] = [model.status[WWTP,L,t].value * model.x[WWTP,L,t].value for t in model.t]
                results[L+'_x_max'] = [model.x_max[WWTP,L].value for t in model.t]
                results[L+'_x_max_u'] = [sum(model.u[WWTP,L,t].value for t in model.t) * model.x_max[WWTP,L].value for t in model.t]
                results[L+'_status'] = [model.status[WWTP,L,t].value for t in model.t]
                results[L+'_x'] = [model.x[WWTP,L,t].value for t in model.t]
                results [L + '_opex'] = [model.opex_monthly[WWTP,L,t].value for t in model.t]
                results[L+'_z'] = [model.z[WWTP,L,t].value for t in model.t]
                results[L+'_b'] = [model.b[WWTP,L,t].value for t in model.t]
                results[L+'_u'] = [model.u[WWTP,L,t].value for t in model.t]
                results[L+'_zeta'] = [model.zeta[WWTP,L,t].value for t in model.t]
                
                removal = np.zeros(len(model.t))
                conc = np.zeros(len(model.t))
                SS_conc_lim = np.ones(len(model.t)) * model.SS_rem_per[WWTP] * 100
                L2_per_lim = np.ones(len(model.t)) * 15
                L3_per_lim = np.ones(len(model.t)) * 6
                for t in model.t:
                    if model.status[WWTP,L,t]() > 0:
                        removal[t] = (model.x[WWTP,L,t]())/ model.dis[WWTP, t]() * 100
                        conc[t] = (model.dis[WWTP, t]() - model.x[WWTP,L,t]())/ model.flow[WWTP,t]() * self.lbNpermgd_to_mgNperL       
                    SS_conc_lim[t] = (model.dis[WWTP, t]() * (1- model.SS_rem_per[WWTP]))/ model.flow[WWTP,t]() * self.lbNpermgd_to_mgNperL
                    L2_per_lim[t] = (model.dis[WWTP,t]() - L2_per_lim[t] * model.flow[WWTP,t]()/ self.lbNpermgd_to_mgNperL)/ model.dis[WWTP, t]() * 100
                    L3_per_lim[t] = (model.dis[WWTP,t]() - L3_per_lim[t] * model.flow[WWTP,t]()/ self.lbNpermgd_to_mgNperL)/ model.dis[WWTP, t]() * 100
                results[L+'_per_removal'] = removal
            results['SS_per_lim'] = np.ones(len(model.t)) * model.SS_rem_per[WWTP] * 100
            results['L2_per_lim'] = L2_per_lim
            results['L3_per_lim'] = L3_per_lim
            results['SS_conc_lim'] = SS_conc_lim
            results['L2_conc_lim'] = np.ones(len(model.t)) * 15
            results['L3_conc_lim'] = np.ones(len(model.t)) * 6

            results.to_csv(self.figpath +'results_'+WWTP+'.csv')

            # print flow results
            for WWTP in model.WWTP:
                #print TIN removal results
                results_flow = pd.DataFrame(index=self.datetime)
                results_flow['Required_removal'] =[value(model.dis_minus_reg[WWTP,t]) for t in model.t]
                results_flow['Influent_flow'] = [model.flow[WWTP,t].value for t in model.t]
                results_flow['Influent_load'] = [model.dis[WWTP,t].value for t in model.t]
                results_flow['Influent_conc'] = [model.influent_conc[WWTP,t].value for t in model.t]
                results_flow['Total_removal'] = [model.r[WWTP,t].value for t in model.t]
                results_flow['Effluenct_conc'] = [(model.dis[WWTP,t].value - model.r[WWTP,t].value)/model.flow[WWTP,t].value * self.lbNpermgd_to_mgNperL for t in model.t] 
                for L in model.L:
                    results_flow[L+'_r'] = [model.status[WWTP,L,t].value * model.x[WWTP,L,t].value for t in model.t]
                    results_flow[L+'_x_flow'] = [model.x_flow[WWTP,L,t].value for t in model.t]
                results_flow.to_csv(self.figpath +'results_flow_'+WWTP+'.csv')

            # print individual economic WWTP results
            results_econ = pd.DataFrame(index=self.datetime_years)
            for L in model.L:
                results_econ[L+'_capex'] = [model.capex_yearly_NPV[WWTP,L,year].value for year in model.years]
                results_econ[L+'_opex'] = [model.opex_yearly_NPV[WWTP,L,year].value for year in model.years]
            results_econ.to_csv(self.figpath +'results_econ_'+WWTP+'.csv')
            
        return model
    
    def build(self):
        """
        Builds the optimization model for WWTP:
            - Add parameters from datafile (regulations, bounds of upgrades, capex, opex)
            - Add variables (nutrient removal by each upgrade, binary variables)
            - Add constraints (capactity constraint, regulatory constraint, integer constraint)
            - Add objective (minimize total cost)
        
        """

        model = ConcreteModel()

        # get WWTP data
        df = self.get_WWTP_data()

        model.t = range(len(self.datetime))
        model.WWTP = self.WWTP
        model.L = ['SS', 'L2', 'L2upg3', 'L3']                      # number of upgrades
        model.years = range(len(self.datetime_years))

        
        model.DualReductions = 0
        
        # Add parameters
        model = self.add_regulation_params(model, df)
        model = self.add_upgrade_bounds(model, df)
        model = self.add_capex_params(model, df)
        model = self.add_opex_params(model, df)

        
        # Add variables
        model = self.add_upgrade_variables(model)
        
        # Add constraint if joint_infrastructure_occurs
        
        model = self.fix_capex_investment_constraints(model)

        
        # Add constraints
        model = self.add_capacity_constraints(model)
        #model = self.add_regulatory_constraints(model, self.Constraint_tag)
        model = self.add_flow_capacity_constraints(model)
        model = self.add_max_capacity_constraints(model)
        model = self.add_build_upgrade_constraint(model)
        model = self.add_integer_constraints(model)
        model = self.add_max_removal_upgrade_constraint(model)

                
        model = self.add_trading_market_constraint(model)
        
        
        
        model = self.check_trading(model)
        


        
        # Set objectives
        model = self.calculate_capex(model)
        model = self.calculate_opex(model)
        model = self.calculate_total_cost(model)
        model = self.add_objective(model, self.Objective_tag)
        
        return model

        
    def add_upgrade_bounds(self, model, df):
        
        '''
        Function that adds the upper and lower
        bounds for each upgrade to the model
        values are taken from imported datafile
        '''
        
        ## define bounds for each upgrade 
        
        upgrade_bound_tags = {'SS': self.bounds_SS_tag, 'L2': self.bounds_L2_tag, 'L2upg3': self.bounds_L2upg3_tag, 'L3': self.bounds_L3_tag}
        upgrade_bound_max_tags = {'SS': self.bounds_SS_max_tag, 'L2': self.bounds_L2_max_tag, 'L2upg3': self.bounds_L2upg3_max_tag, 'L3': self.bounds_L3_max_tag}
        
        # if projected discharge multiplier > 1:
        # increase upper bound of all upgrades by the same factor
        mult = 1
        if self.projection_multiplier > 1:
            mult = self.projection_multiplier 


        LB = {(i, upgrade): df.loc[i, upgrade_bound_tags[upgrade][0]] for upgrade in self.L for i in self.WWTP}
        UB = {(i, upgrade): df.loc[i, upgrade_bound_tags[upgrade][1]] * mult for upgrade in self.L for i in self.WWTP}
        

        # The bounds for x_max removal are not multiplied by the projection multiplier
        # Since, the capex is based on the upper bound of the upgrade provided by BACWA
        # Therefore, this places an upper bound on how large the upgrade can be (unless a capex costing function is provided)
        # i.e. For the given capex, this is the largest TIN removal that can be achieved with this upgrade
        LB_max = {(i, upgrade): df.loc[i, upgrade_bound_max_tags[upgrade][0]] for upgrade in self.L for i in self.WWTP}
        UB_max = {(i, upgrade): df.loc[i, upgrade_bound_max_tags[upgrade][1]] for upgrade in self.L for i in self.WWTP}

        # Find UB_max for all upgrades:
        self.x_max_allupgrades = max(
            UB_max[(i, upgrade)]
            for upgrade in self.L
            for i in self.WWTP
        )

        model.UB = Param(model.WWTP, model.L, initialize=UB, mutable=True)
        model.LB = Param(model.WWTP, model.L, initialize=LB, mutable=True)

        model.UB_max = Param(model.WWTP, model.L, initialize=UB_max, mutable=True)
        model.LB_max = Param(model.WWTP, model.L, initialize=LB_max, mutable=True)

        
        # define time-dependent bounds for each upgrade
        
        SS_rem_per = {i: df.loc[i, self.SS_per_removal_tag] for i in self.WWTP}
        model.SS_rem_per = Param(model.WWTP, initialize=SS_rem_per, mutable=False)

        SS_flow_cap = {i: df.loc[i, self.SS_flow_cap_tag] for i in self.WWTP}
        model.SS_flow_cap = Param(model.WWTP, initialize=SS_flow_cap, mutable=False)


        return model


    def add_upgrade_variables(self, model):
        """
        Variable for the amount of nutrient removed 
        by each upgrade for each WWTP
        """
        
        def fb(model, WWTP, L, t):
            return (model.LB[WWTP, L], model.UB[WWTP, L])
        
        def fb_max(model, WWTP, L):
            return (model.LB_max[WWTP, L], model.UB_max[WWTP, L])
        
        def fb_flow_max(model, WWTP, L):
            if L == 'SS':
                return (0, model.SS_flow_cap[WWTP])
            else:
                return (0, None)
        
        def x_init(model, WWTP, L, t):
            return model.LB[WWTP, L]
        
        def x_max_init(model, WWTP, L):
            return model.LB_max[WWTP, L]

        model.x = Var(model.WWTP, model.L, model.t, bounds=fb, initialize=x_init)    # total nitrogen removed by each facility at each timestep
        model.x_flow = Var(model.WWTP, model.L, model.t, bounds=(0,None), initialize=0)    # flow diverted into each upgrade in each facility at each timestep (assuming upgrade operates at full operational capacity ex. 6 mg/L or 15 mg/L)

        if self.Constraint_tag == 'No_coordination':
            model.x_max = Var(model.WWTP, model.L, bounds=fb_max, initialize=x_max_init)    # Maximum nitrogen removed by each facility by each upgrade
            model.x_flow_max = Var(model.WWTP, model.L, bounds=fb_flow_max, initialize=0)    # Maximum flow that can be diverted into each upgrade in each facility (assuming upgrade operates at full operational capacity ex. 6 mg/L or 15 mg/L)
        
        model.r = Var(model.WWTP, model.t, initialize=0)                      # total nitrogen removed by each facility at each timestep

        return model
    
    
    def add_capex_params(self, model, df):
        '''
        Capital cost estimates for each upgrade
        based on the BACWA 2017 Report
        '''
        
        #tags
        capex_tags = {'SS': self.capex_SS_tag, 'L2': self.capex_L2_tag, 'L2upg3': self.capex_L2upg3_tag, 'L3': self.capex_L3_tag}    
        capex_tags_power = {'SS': 0, 'L2': self.capex_L2_power_tag, 'L2upg3': self.capex_L2upg3_power_tag, 'L3': self.capex_L3_power_tag}

        # if linear: capital cost (D*x + E)
        model.D = {(i, upgrade) : df.loc[i, capex_tags[upgrade][0]] for upgrade in model.L for i in self.WWTP}
        model.E = {(i, upgrade) : df.loc[i, capex_tags[upgrade][1]] for upgrade in model.L for i in self.WWTP}

        # if power law: capital costs (alpha* x^beta)
        model.alpha = {(i, upgrade) : df.loc[i, capex_tags_power[upgrade][0]] if upgrade in self.capex_costing_power else 0 for upgrade in model.L for i in self.WWTP}
        model.beta = {(i, upgrade) : df.loc[i, capex_tags_power[upgrade][1]] if upgrade in self.capex_costing_power else 0 for upgrade in model.L for i in self.WWTP}

        return model
    

    def add_opex_params(self, model, df):
        '''
        Capital cost estimates for each upgrade
        based on the BACWA 2017 Report
        Opex reported as mil $/year
        Tag will be divided by 12 to reflect monthly costs
        '''
        opex_tags = {'SS': self.opex_SS_tag, 'L2': self.opex_L2_tag, 'L2upg3': self.opex_L2upg3_tag, 'L3': self.opex_L3_tag} 


        # operating cost (A*x + B) per month 
        model.A = {(i, upgrade) : df.loc[i, opex_tags[upgrade][0]]/12 for upgrade in self.L for i in self.WWTP}
        model.B = {(i, upgrade) : df.loc[i, opex_tags[upgrade][1]]/12 for upgrade in self.L for i in self.WWTP}

        return model


    def add_integer_variables(self, model):
        """
        Add integer variable that determines if an upgrade is built
        """

        
        model.z = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that is 1 when the upgrade is being built and operated')
        model.b = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that is 1 from when the upgrade finishes being built')
        model.u = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that is 1 at the exact time when an upgrade starts being built and 0 otherwise')
        model.op_start = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that is 1 at the exact time when an upgrade starts being operated and 0 otherwise')
        model.zeta = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that determines when an upgrade build is completed')
        model.status = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that determines when an upgrade is operated after built is completed')
        

        # Fix initial z at 0
        model.b[:,:,0].fix(0)
        model.u[:,:,0].fix(0)
        model.zeta[:,:,0].fix(0)


        return model


    def set_integer_variables(self,model):
        """
        Set integer variables
        Unfix variables for technologies used in the model
        """
        

        if not self.include_L3:
            model.b[:,'L3',:].fix(0)
            model.u[:,'L3',:].fix(0)
            model.zeta[:,'L3',:].fix(0)
        
        if not self.include_L2:
            model.b[:,'L2',:].fix(0)
            model.u[:,'L2',:].fix(0)
            model.zeta[:,'L2',:].fix(0)
        
        if not self.include_L2upg3:
            model.b[:,'L2upg3',:].fix(0)
            model.u[:,'L2upg3',:].fix(0)
            model.zeta[:,'L2upg3',:].fix(0)
        
        if not self.include_SS:
            model.b[:,'SS',:].fix(0)
            model.u[:,'SS',:].fix(0)
            model.zeta[:,'SS',:].fix(0)

        for WWTP in model.WWTP:
            for L in model.L:
                if model.LB[WWTP, L].value == 0 and model.UB[WWTP, L].value == 0:
                    model.b[WWTP, L, :].fix(0)
                    model.u[WWTP, L, :].fix(0)
                    model.zeta[WWTP, L, :].fix(0)

        if not self.staged_infrastructure:
            print('Staged infrastructure is not allowed')
            # fix all integer variables to zero
            model.u.fix(0)
            # only unfix integer variables when the upgrade needs to be built
            for WWTP in model.WWTP:
                ## find when the upgrade needs to be operated (when discharge exceeds regulation)
                t_operate = np.where(np.array([value(model.dis_minus_reg[WWTP, t]) for t in model.t]) > 0)[0][0]
                ## unfix upgrade for when the upgrade needs to be built
                t_build = t_operate - 12 * self.time_to_build_yr 
                model.u[WWTP,:,t_build].unfix()
        
        return model


    def add_trading_market_constraint(self, model):
        
        """
        If trading market is not allowed:
            - add constraint that each WWTP must meet its own discharge limit in each year
        
        If trading market is allowed at a certain year, add constraint to remove market in previous years:
            - add requirement that each WWTP must meet its own discharge limit in each year
        """
        
        if not self.trading_market:
            self.trading_market_year = None    
        
        try:
            year = self.datetime_years[self.trading_market_year].year 
            ind_end = np.where(self.datetime.year == year)[0][-1] - len(self.datetime.year[self.datetime.year == year])
            print('Trading market starts in year:', self.trading_market_year)
            '''
            print('year:', year) 
            print('ind_end:', ind_end)
            print('date at end index:', self.datetime[ind_end])
            print('t at end index:', model.t[ind_end])
            '''
        except: 
            print('Assuming trading market is never established')
            print('Requiring all infrastructure to meet their own individual permits')
            ind_end = len(self.datetime)

        self.ind_end_trading_market_year = ind_end
        # Constraint that the total WWTP discharge must be less than the WWTP regulation
        def regulation(model, WWTP, t):
            if t <= ind_end:
                return model.r[WWTP,t] >= model.dis_minus_reg[WWTP,t]
            else:
                return sum(model.r[WWTP,t] for WWTP in model.WWTP) >= sum(model.dis_minus_reg[WWTP,t] for WWTP in model.WWTP)
        
        model.regulation = Constraint(model.WWTP, model.t, rule=regulation)

        return model

    def check_trading(self, model):
        """
        Creates binary variable to check if WWTP is removing in excess of its own discharge limit (i.e. potentially trading)
        or if WWTP is removing less than its own discharge limit (i.e. definitely buying)
        """
        model.status_buying = Var(model.WWTP, model.t, within=Binary, initialize=0, doc='Binary variable that is 1 when the WWTP is buying (removing less than its own discharge limit) and 0 otherwise')
        model.excess_removal = Var(model.WWTP, model.t, within=Reals, initialize=0, doc='Variable that is positive when the WWTP is removing in excess of its own discharge limit and negative when the WWTP is removing less than its own discharge limit')

        def calculate_excess_removal(model, WWTP, t):
            return model.excess_removal[WWTP,t] == model.r[WWTP,t] - model.dis_minus_reg[WWTP,t]
        
        model.calculate_excess_removal = Constraint(model.WWTP, model.t, rule=calculate_excess_removal)

        def check_buying_credits(model, WWTP, t):
            #print('t:', t, 'ind_end_trading_market_year:', self.ind_end_trading_market_year)
            if t <= self.ind_end_trading_market_year:
                return model.status_buying[WWTP,t] == 0
            else:
                # if excess_removal is negative, then status_buying is 1
                # if excess_removal is positive, then status_buying can be 0 or 1
                # if excess_removal is zero, then status_buying can be 0 or 1
                return (1 - model.status_buying[WWTP,t]) * model.excess_removal[WWTP, t] >= 0
        
        def check_buying_credits_2(model, WWTP, t):
            if t <= self.ind_end_trading_market_year:
                return Constraint.Skip
            else:
                # if excess_removal is positive, then status_buying is 0 
                # if excess_removal is negative, then status_buying can be 0 or 1
                # if excess_removal is zero, then status_buying can be 0 or 1
                return model.status_buying[WWTP,t] * model.excess_removal[WWTP, t] <= 0
            
        # if required removal (discharge minus regulation) is negative or zero, then status_buying must be 0 (not buying)
        def check_zero_removal(model, WWTP, t):
            if model.dis_minus_reg[WWTP,t] > 0:
                return Constraint.Skip
            else:
                return model.status_buying[WWTP,t] == 0
                
                
        
        model.check_buying_credits = Constraint(model.WWTP, model.t, rule=check_buying_credits)
        model.check_buying_credits_2 = Constraint(model.WWTP, model.t, rule=check_buying_credits_2)
        model.check_zero_removal = Constraint(model.WWTP, model.t, rule=check_zero_removal)

        # Add trading ratio:
        try:
            TR = self.TR
            print(f'Trading ratio (excess treatment to meet compliance): {TR:.1f}:1 Ratio')
        except:
            TR = 1
            print(f'params["TR"] is not defined --> Assuming 1:1 Trading Ratio since')

        def add_trading_ratio(model, t):
            if t <= self.ind_end_trading_market_year:
                return Constraint.Skip
            else:
                return sum((1- model.status_buying[WWTP,t]) * model.excess_removal[WWTP,t] for WWTP in model.WWTP) >= TR * sum(model.status_buying[WWTP2,t] * (-model.excess_removal[WWTP2,t]) for WWTP2 in model.WWTP)

        if TR > 1:
            model.trading_ratio_constraint = Constraint(model.t, rule=add_trading_ratio)
        
        return model

    def fix_capex_investment_constraints(self, model):
        """
        Fix capex investment constraints for opex only model
        LP_model
        """
        if not self.trading_market:
            print('Trading market is not allowed')
            print('Running MILP model to optimize infrastructure to meet individual discharge limits')
            self.unfix_infrastructure_year = None
            model = self.add_integer_variables(model)
            model = self.set_integer_variables(model)
            return model
        
        try:
            year = self.datetime_years[self.unfix_infrastructure_year].year 
            ind_end = np.where(self.datetime.year == year)[0][-1] - len(self.datetime.year[self.datetime.year == year])
            if not self.joint_infrastructure:
                print('Joint infrastructure is not allowed')
                print('Fixing infrastructure that meets individual discharge limits')
                ind_end = len(self.datetime)
            else:
                print('Joint infrastructure planning starts at year:', self.unfix_infrastructure_year)
            '''
            print('year:', year) 
            print('ind_end:', ind_end)
            print('date at end index:', self.datetime[ind_end])
            print('t at end index:', model.t[ind_end])
            '''   

        except: 
            print('Assuming joint infrastructure is never established')
            print('Fixing infrastructure to meet individual discharge limits')
            ind_end = len(self.datetime)

        
        
        # For x_max we need to redefine x_max
        def fb_max(model, WWTP, L):
            return (model.LB_max[WWTP, L], model.UB_max[WWTP, L])
        
        def x_max_init(model, WWTP, L):
            return model.LB_max[WWTP, L]

        def fb_flow_max(model, WWTP, L):
            if L == 'SS':
                return (0, model.SS_flow_cap[WWTP])
            else:
                return (0, None)
        
        
        # Fix all upgrades before start year
        z_fix = {}; b_fix = {}; u_fix = {}; op_fix = {}; zeta_fix = {}; status_fix = {}; x_max_fix = {}

        for WWTP in model.WWTP:
            try:
                path = self.figpath_capex +'results_'+ WWTP +'.csv'
            except:
                if self.Constraint_tag == 'Partial_coordination':
                    raise SystemExit('Cannot find data for prior infrastructure investments to run Partial Coordination model')
                print('Cannot find data for prior infrastructure investments')
                print('Running MILP model with all infrastructure unfixed')
                
                # redefine x_max
                model.x_max = Var(model.WWTP, model.L, bounds=fb_max, initialize=x_max_init)    # Maximum nitrogen removed by each facility by each upgrade
                model.x_flow_max = Var(model.WWTP, model.L, bounds=fb_flow_max, initialize=0)    # Maximum flow that can be diverted into each upgrade in each facility (assuming upgrade operates at full operational capacity ex. 6 mg/L or 15 mg/L)
                model = self.add_integer_variables(model)
                model = self.set_integer_variables(model)
                return model
            
            df = pd.read_csv(path)
            z_fix = {**z_fix, **{(WWTP, L, t): int(round(float(df.loc[t, L+'_z']))) for L in sorted(model.L) for t in sorted(model.t)}}
            b_fix = {**b_fix, **{(WWTP, L, t): int(round(float(df.loc[t, L+'_b']))) for L in sorted(model.L) for t in sorted(model.t)}}
            u_fix = {**u_fix, **{(WWTP, L, t): int(round(float(df.loc[t, L+'_u']))) for L in sorted(model.L) for t in sorted(model.t)}}
            x_max_fix = {**x_max_fix, **{(WWTP, L): float(df.loc[0, L+'_x_max']) for L in model.L}}

        
        model.z = Var(model.WWTP, model.L, model.t, within=Binary, initialize= z_fix, doc='Binary variable that is 1 from when the upgrade starts being built')
        model.b = Var(model.WWTP, model.L, model.t, within=Binary, initialize= b_fix, doc='Binary variable that is 1 from when the upgrade finishes being built')
        model.u = Var(model.WWTP, model.L, model.t, within=Binary, initialize= u_fix, doc='Binary variable that is 1 at the exact time when an upgrade starts being built and 0 otherwise')
        
        model.op_start = Var(model.WWTP, model.L, model.t, within=Binary, initialize= 0, doc='Binary variable that is 1 at the exact time when an upgrade starts being operated and 0 otherwise')
        model.zeta = Var(model.WWTP, model.L, model.t, within=Binary, initialize= 0, doc='Binary variable that determines when an upgrade build is completed')
        model.status = Var(model.WWTP, model.L, model.t, within=Binary, initialize= 0, doc='Binary variable that determines when an upgrade is operated after built is completed')
        model.x_max = Var(model.WWTP, model.L, initialize= x_max_fix, bounds=fb_max, doc='Maximum nitrogen removed by each facility by each upgrade')
        model.x_flow_max = Var(model.WWTP, model.L, bounds=fb_flow_max, initialize=0)    # Maximum flow that can be diverted into each upgrade in each facility (assuming upgrade operates at full operational capacity ex. 6 mg/L or 15 mg/L)

        for t in range(0, ind_end-1):
            model.z[:,:,t].fix()
            model.b[:,:,t].fix()
            model.u[:,:,t].fix()
            # only fix x_max of upgrades that are already built
            for WWTP in model.WWTP:
                for L in model.L:
                    if z_fix[WWTP,L,t]:
                        model.x_max[WWTP,L].fix()
        
        # does not allow building certain upgrades if they are not included in the model
        # fixes SS upgrade at 0 if it is not an option for a WWTP
        model = self.set_integer_variables(model)

        return model

    
    def add_regulation_params(self, model, df):
        """
        Add regulatory parameters to the model
        based on current discharge of each WWTP
        and regulations from Water Board SF Bay 2024.

        
        If Current discharge: SF Bay Water Board Nutrients Watershed Permit R2-2024-0023
            - Average dry season loads (kg/day) for 2019-2023
            - Units: kg/day
        
        If Current discharge: ECHO database
            - Average dry season loads (kg/day) and dry season flow (mgd) from 2019-07-31 to 2024-04-30 
            - Values for WWTP downloaded from ECHO database (https://echo.epa.gov/)

        
        Projected discharge: BACWA 2017 Report Table: 
            -projected discharge loads are based on the 2015 BACWA Nutrient Reduction Study Group Annual Report 
            (data from 7/2012-6/2015) and are projected forward to the midpoint of the planning period. 
            - The reported flows and loads for optimization, upgrades, and sideestream represent average projected load reduction 
            for the period of analysis (10-yr for optimization and 30-yr for upgrades and sidestream).
            - Table 5-2 "The loads represent average projected loads discharged to the Bay for the period of analysis (30-yr for sidestream)."
        
        Interim/Final effluent limitations: "NPDES PERMIT CA0038873 (May 2024) in kg/day"
        """

        # nutrient discharge for each WWTP
        ## assumes linear increase in discharge from current to projected level
        discharge = pd.DataFrame(index=self.datetime, columns=df.index)
        for i in model.WWTP:
            if self.use_NPDES_for_current_TN_discharge:
                current = df.loc[i, self.discharge_NPDES_current_tag] * 2.204623                             # convert kg/day to lbs/day
            elif self.use_ECHO_for_current_TN_discharge:
                current = df.loc[i, self.discharge_ECHO_current_tag] * 2.204623                             # convert kg/day to lbs/day
            else:
                raise SystemExit('specify how to calculate current discharge')
            
            projected = df.loc[i, self.discharge_BACWA_projected_tag] * self.projection_multiplier
            if self.projected_flow_assumption == 'linear':
                discharge[i] = np.linspace(current, projected, 
                                            len(self.datetime), endpoint=True)
            elif self.projected_flow_assumption == 'exponential':
                growth_rate_annual = (projected / current)**(1/len(self.datetime_years)) - 1
                #discharge[i] = current * (1 + growth_rate_annual) ** (self.datetime.year - self.datetime.year[0])
                discharge_linear = np.linspace(current, projected, len(self.datetime), endpoint=True)
                projected_final_step = np.where(self.datetime == '2054-09-01')[0][0]
                projected_new = discharge_linear[projected_final_step]
                growth_rate_monthly = (projected_new / current)**(1/len(self.datetime[:projected_final_step])) - 1
                discharge[i] = current * (1 + growth_rate_monthly) ** (np.arange(len(self.datetime)))
            else:
                raise SystemExit('specify params["projected_flow_assumption"] as linear or exponential')
        
        # regulations for each WWTP
        regulations = pd.DataFrame(index=self.datetime, columns=df.index)
        for i in model.WWTP:
            regulations.loc[:, i] = df.loc[i, self.reg_current_tag] * 2.204623                                       # convert kg/day to lbs/day
            regulations.loc[self.datetime >= self.new_reg_year, i] = df.loc[i, self.reg_projected_tag]* 2.204623    # convert kg/day to lbs/day
            if self.seasonal_regulation:
                regulations.loc[self.datetime.month.isin([1,2,3,4,10,11,12]), i] = 10000000000

        discharge_minus_regulations = pd.DataFrame(index=self.datetime, columns=df.index)
        for i in model.WWTP:
            discharge_minus_regulations[i] = discharge[i] - regulations[i]
            # replace lower bound with 0
            discharge_minus_regulations[i] = discharge_minus_regulations[i].clip(lower=0)
            if discharge_minus_regulations[i].iloc[0] > 0:
                raise SystemExit('Initial discharge is greater than interim regulation for WWTP:', i)


        reg_dict = {(WWTP,t): regulations[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        dis_dict = {(WWTP,t): discharge[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        #dis_minus_reg_dict = {(WWTP,t): discharge[WWTP].iloc[t]-regulations[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        dis_minus_reg_dict = {(WWTP,t): discharge_minus_regulations[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        
        model.reg = Param(model.WWTP, model.t, initialize=reg_dict, mutable=True)
        model.dis = Param(model.WWTP, model.t, initialize=dis_dict, mutable=True)
        model.dis_minus_reg = Param(model.WWTP, model.t, initialize=dis_minus_reg_dict, mutable=False)

        # Flow for each WWTP
        flow = pd.DataFrame(index=self.datetime, columns=df.index)
        for i in model.WWTP:
            if self.use_ECHO_for_current_TN_discharge:
                current = df.loc[i, self.flow_ECHO_current_tag] 
            else:
                current = df.loc[i, self.flow_BACWA_current_tag]                                      # use BACWA for flow
            projected = df.loc[i, self.flow_BACWA_projected_tag] * self.projection_multiplier
            if self.projected_flow_assumption == 'linear':
                flow[i] = np.linspace(current, projected, len(self.datetime), endpoint=True)
            elif self.projected_flow_assumption == 'exponential':
                growth_rate_annual = (projected / current)**(1/len(self.datetime_years)) - 1
                #flow[i] = current * (1 + growth_rate_annual) ** (self.datetime.year - self.datetime.year[0])
                growth_rate_monthly = (projected / current)**(1/len(self.datetime)) - 1
                flow_linear = np.linspace(current, projected, len(self.datetime), endpoint=True)
                projected_final_step = np.where(self.datetime == '2054-09-01')[0][0]
                projected_new = flow_linear[projected_final_step]
                growth_rate_monthly = (projected_new / current)**(1/len(self.datetime[:projected_final_step])) - 1
                flow[i] = current * (1 + growth_rate_monthly) ** (np.arange(len(self.datetime)))
            else:
                raise SystemExit('specify params["projected_flow_assumption"] as linear or exponential') 
        
        flow_dict = {(WWTP,t): flow[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        model.flow = Param(model.WWTP, model.t, initialize=flow_dict, mutable=True)

        influent_conc_dict = {(WWTP,t): discharge[WWTP].iloc[t] / flow[WWTP].iloc[t] * self.lbNpermgd_to_mgNperL for t in model.t for WWTP in self.WWTP}
        model.influent_conc = Param(model.WWTP, model.t, initialize=influent_conc_dict, mutable=True)

        # define max amount of removal by each upgrade
        L2_bound_discharge = pd.DataFrame(index=self.datetime, columns=df.index)
        L3_bound_discharge = pd.DataFrame(index=self.datetime, columns=df.index)
        
        for i in model.WWTP:
            L2_bound_discharge[i] = discharge[i] - 15 *flow[i] / self.lbNpermgd_to_mgNperL
            L3_bound_discharge[i] = discharge[i] - 6 *flow[i] / self.lbNpermgd_to_mgNperL
            # replace lower bound with 0
            L2_bound_discharge[i] = L2_bound_discharge[i].clip(lower=0)
            L3_bound_discharge[i] = L3_bound_discharge[i].clip(lower=0)
        """
        for WWTP in model.WWTP:
            for t in model.t:
                # L2 can remove TN to reach 15 mg/L
                L2_bound_discharge.loc[t, WWTP] = discharge[WWTP].iloc[t] - 15 *flow[WWTP].iloc[t] / self.lbNpermgd_to_mgNperL
                # L3 can remove TN to reach 6 mg/L
                L3_bound_discharge.loc[t, WWTP] = discharge[WWTP].iloc[t] - 6 *flow[WWTP].iloc[t] / self.lbNpermgd_to_mgNperL
        """

        L2_bound_dict = {(WWTP,t): L2_bound_discharge[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        L3_bound_dict = {(WWTP,t): L3_bound_discharge[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        
        model.L2_bound = Param(model.WWTP, model.t, initialize=L2_bound_dict, mutable=True)
        model.L3_bound = Param(model.WWTP, model.t, initialize=L3_bound_dict, mutable=True)
        
        return model


    def add_integer_constraints(self, model):
        """
        Add integer constraints to the model
        Constraints are:
            1) You can't operate L2 and L3 at the same time
            2) You have to build L2 before upgrading to L2upg3
            3) You can't operate L2upg3 and L3 at the same time
        """

        # Constraint that you can't build L3 if L2 is already built (and vice-versa)
        def L2_L3_constraint(model, WWTP):
            return sum(model.u[WWTP,'L3',t] for t in model.t) <= 1 - sum(model.u[WWTP,'L2',t] for t in model.t)
        model.integer_constraint_L3 = Constraint(model.WWTP, rule=L2_L3_constraint)

        # Constraint that you have to build L2 if you want to build L2upg3
        def L2_L2upg3_build_constraint(model, WWTP):
            return sum(model.u[WWTP,'L2upg3',t] for t in model.t) <= sum(model.u[WWTP,'L2',t] for t in model.t)
        model.integer_constraint_L2upg3_build = Constraint(model.WWTP, rule=L2_L2upg3_build_constraint)

        # Constraint that you cannot build L2upg3 while L2 is being built
        def L2_L2upg3_build_constraint_2(model, WWTP, t):
            return model.zeta[WWTP,'L2upg3',t]  <= 1 - model.zeta[WWTP,'L2',t]
        model.integer_constraint_L2upg3_build_2 = Constraint(model.WWTP, model.t, rule=L2_L2upg3_build_constraint_2)

        # Constraint that you cannot operate L2 when operating to L2upg3
        def L2_L2upg3_constraint(model, WWTP, t):
            return model.status[WWTP,'L2upg3',t]  <= 1- model.status[WWTP,'L2',t]
        model.integer_constraint_L2upg3 = Constraint(model.WWTP, model.t, rule=L2_L2upg3_constraint)

        # Constraint that you have to build L2 before building L2upg3
        def L2_L2upg3_operate_constraint(model, WWTP, t):
            return model.z[WWTP,'L2upg3',t]  <= model.z[WWTP,'L2',t]
        model.integer_constraint_L2upg3_operate = Constraint(model.WWTP, model.t, rule=L2_L2upg3_operate_constraint)

        # Constraint that L2 has to operate at max capacity before operating L2upg3
        def L2upg3_max_constraint(model, WWTP):
            return model.x_max[WWTP,'L2'] >= sum(model.u[WWTP,'L2upg3',t] for t in model.t) * model.UB_max[WWTP, 'L2']
        model.integer_constraint_L2upg3_max = Constraint(model.WWTP, rule=L2upg3_max_constraint)
        

        # Constraint that you can't build L2upg3 if L3 is already built
        def L2upg3_L3_constraint(model, WWTP):
            return sum(model.u[WWTP,'L3',t] for t in model.t) <= 1 - sum(model.u[WWTP,'L2upg3',t] for t in model.t)
        model.integer_constraint_L2upg3L3 = Constraint(model.WWTP, rule=L2upg3_L3_constraint)
        
        return model

    def add_max_removal_upgrade_constraint(self, model):

        # Constraint that SS can only operate at the max limit removal of current discharge
        def SS_bound_constraint(model, WWTP, t):
            return model.x[WWTP,'SS',t]*model.status[WWTP,'SS',t]  <= model.SS_rem_per[WWTP] * model.dis[WWTP, t]
        
        model.SS_upper_bound = Constraint(model.WWTP, model.t, rule=SS_bound_constraint)
    
        # Constraint that L2 can only operate to produce 15 mg/L of TN
        def L2_bound_constraint(model, WWTP, t):
            return model.x[WWTP,'L2',t]*model.status[WWTP,'L2',t]  <= model.L2_bound[WWTP,t]
            
        model.L2_upper_bound = Constraint(model.WWTP, model.t, rule=L2_bound_constraint)

        # Constraint that L3 can only operate to produce 6 mg/L of TN
        def L3_bound_constraint(model, WWTP, t):
            return model.x[WWTP,'L3',t]*model.status[WWTP,'L3',t]  <= model.L3_bound[WWTP,t]
        
        model.L3_upper_bound = Constraint(model.WWTP, model.t, rule=L3_bound_constraint)

        # Constraint that L2 upgraded to L2upg3 can only operate to produce 6 mg/L of TN
        def L2upg3_bound_constraint(model, WWTP, t):
            return model.x[WWTP,'L2upg3',t] * model.status[WWTP,'L2upg3',t]  <= model.L3_bound[WWTP,t]
        
        model.L2upg3_upper_bound = Constraint(model.WWTP, model.t, rule=L2upg3_bound_constraint)
        
        return model
    
    
    
    def add_capacity_constraints(self, model):
        """
        Add Capacity constraints to the model
        This function calculates r(WWTP,t) which represents the total 
        amount of nutrients removed by each WWTP at each timestep
        """

        
        
        # Constraint that total removal of WWTP at timestep (t) is the current capacity + added capacity
        def current_capacity(model, WWTP, t):
            return model.r[WWTP,t] == (
                sum(
                    model.status[WWTP,L,t] *
                    model.x[WWTP,L,t]for L in model.L
                    )
            )
        
        model.current_capacity_cond = Constraint(model.WWTP, model.t, rule=current_capacity)

        return model

    
    def add_regulatory_constraints(self, model):
        
        """
        Add Constraints that total amount of nutrients discharged into the subembayment
        must be less than the sum of limits of all WWTPs.
        
        If a trading market is not established, then the individual discharge of each WWTP 
        must meet each of their limits. 

        """
        
        # Constraint that the total WWTP discharge by all WWTP in the subembayment must be less than the sum of WWTP regulations
        def regulation(model, t):
            return sum(model.r[WWTP,t] for WWTP in model.WWTP) >= sum(model.dis_minus_reg[WWTP,t] for WWTP in model.WWTP)
        model.regulation = Constraint(model.t, rule=regulation)

        return model


    def add_build_upgrade_constraint(self, model):
        """
        Binary variable to determine if the NMS is built
        """

        self.time_to_build = 12 * self.time_to_build_yr
                
        # Constraint that finds b: when upgrade should be built
        def find_b(model, WWTP, L, t):
            if t < self.time_to_build:
                return model.b[WWTP, L,t] == 0
            else:
                # b is 1 if status has switched to 1 at any point
                return model.b[WWTP, L, t] >= model.status[WWTP, L, t]
        
        model.find_b = Constraint(model.WWTP, model.L, model.t, rule=find_b)

        def update_b(model, WWTP, L, t):
            if t ==0:
                return model.b[WWTP,L,t] == 0
            else:
                # Once b is 1, it stays 1
                return model.b[WWTP, L, t] >= model.b[WWTP, L, t-1]
        
        model.update_b = Constraint(model.WWTP, model.L, model.t, rule=update_b)

        
        # Upgrade starts operating (op_start = 1) when b switches to 1
        def find_op_start(model, WWTP, L, t):
            if t == 0:
                return model.op_start[WWTP, L,t] == 0
            else:
                # op switches to 1 when b switches to 1
                return model.op_start[WWTP, L, t] >= model.b[WWTP, L, t] - model.b[WWTP, L, t-1]
        
        model.find_op_start = Constraint(model.WWTP, model.L, model.t, rule=find_op_start)

        # Upgrade is build (u=1) at start of operation - time_to_build
        def time_to_build(model,WWTP,L,t):
            # if t is less than the time to build, then the upgrade cannot be built
            if t > len(self.datetime) - self.time_to_build - 1:
                return model.u[WWTP,L,t] == 0
            else:
                return model.u[WWTP,L,t] >= model.op_start[WWTP,L,t + self.time_to_build]     

        model.time_to_build = Constraint(model.WWTP, model.L, model.t, rule=time_to_build)
        
        # zeta is 1 while the upgrade is being built
        def find_zeta(model,WWTP,L,t):
            if t < self.time_to_build:
                return model.zeta[WWTP,L,t] == sum(model.u[WWTP,L,t-a] for a in range(t))
            else:
                return model.zeta[WWTP,L,t] == sum(model.u[WWTP,L,t-a] for a in range(self.time_to_build))     

        model.find_zeta = Constraint(model.WWTP, model.L, model.t, rule=find_zeta)

        # z is one while upgrade is being built and operated
        def find_z(model, WWTP, L, t):
            return model.z[WWTP, L, t] == model.zeta[WWTP, L, t] + model.b[WWTP, L, t]
        
        model.find_z = Constraint(model.WWTP, model.L, model.t, rule=find_z)

        return model
    
    
    def add_flow_capacity_constraints(self, model):
        """
        Add flow capacity constraints to the model
        This function calculates the maximum flow that can be diverted into each upgrade in each facility (assuming upgrade operates at full operational capacity ex. 6 mg/L or 15 mg/L)
        """

        # Function that calculates the flow that can be diverted into each upgrade in each facility (assuming upgrade operates at full operational capacity ex. 6 mg/L or 15 mg/L)
        def flow_upgrade_constraint(model, WWTP, L, t):
            if L == 'SS':
                # SS can treat the entire flow of the WWTP 
                #return model.x_flow[WWTP, L, t] == model.status[WWTP, L, t] * model.flow[WWTP, t]
                if model.dis_minus_reg[WWTP,t] > 0 and model.SS_rem_per[WWTP] > 0:
                    # ratio of how much the SS currently removes to the max amount it could remove multiplied by the SS_flow_capacity
                    return model.x_flow[WWTP, L, t] == (model.status[WWTP, L, t] * model.x[WWTP, L, t]) / (model.SS_rem_per[WWTP] *model.dis[WWTP, t]) * model.SS_flow_cap[WWTP]
                else:
                    return model.x_flow[WWTP, L, t] == 0
                # model.SS_rem_per[WWTP] * model.dis[WWTP, t]
            elif L == 'L2':
                # L2 can treat the flow to remove up enough TIN to reach an effluent of 15 mg/L of TN
                return model.x_flow[WWTP, L, t] == model.status[WWTP, L, t] * model.x[WWTP, L, t] / (model.influent_conc[WWTP, t]- 15) * self.lbNpermgd_to_mgNperL
                #return Constraint.Skip
            elif L == 'L3':
                # L3 can treat the flow to remove up enough TIN to reach an effluent of 6 mg/L of TN
                return model.x_flow[WWTP, L, t] == model.status[WWTP, L, t] * model.x[WWTP, L, t] / (model.influent_conc[WWTP, t]- 6) * self.lbNpermgd_to_mgNperL
                #return Constraint.Skip
            elif L == 'L2upg3':
                # L2upg3 can treat the flow to remove up enough TIN to reach an effluent of 6 mg/L of TN
                return model.x_flow[WWTP, L, t] == model.status[WWTP, L, t] * model.x[WWTP, L, t] / (model.influent_conc[WWTP, t]- 6) * self.lbNpermgd_to_mgNperL
                #return Constraint.Skip

        model.flow_upgrade_constraint = Constraint(model.WWTP, model.L, model.t, rule=flow_upgrade_constraint)

        # Constraint that max removal has to be greater than current removal
        def max_flow_capacity(model, WWTP, L, t):
            return model.x_flow_max[WWTP, L] >= model.x_flow[WWTP,L,t]
        
        model.max_flow_capacity = Constraint(model.WWTP, model.L, model.t, rule=max_flow_capacity)
        
        return model
    
    
    
    
    def add_max_capacity_constraints(self, model):
        """
        Get the maximum amount of nutrients removed to calculate
        the capital cost of infrastructure
        """
        
        # Constraint that max removal has to be greater than current removal
        def max_capacity(model, WWTP, L, t):
            return model.x_max[WWTP, L] >= model.x[WWTP,L,t]
        
        # Constraint that removal (x) has to be x_lowerbound when not built
        def non_operational_x(model, WWTP, L, t):
            return model.x[WWTP, L, t] * (1 - model.status[WWTP, L, t]) <= model.LB[WWTP, L] 

    
        model.max_capacity = Constraint(model.WWTP, model.L, model.t, rule=max_capacity)
        model.non_operational_x_cond = Constraint(model.WWTP, model.L, model.t, rule=non_operational_x)

        return model


    def add_objective(self, model, Objective_tag):
        """
        Add objective to model
        Define annual interest rate in json file
        Parameters for opex and capex based on add_opex and add_capex functions
        """
                        
        # Minimize total cost
        model.value = Objective(expr=model.total_cost, sense=minimize)

        return model


    def get_WWTP_data(self):
        '''
        WWTP dataset includes information on:
            - Abbreviation for each WWTP
            - Current (2020) and projected (2045) TIN discharge of each WWTP
            - Regulations on TIN discharge for each WWTP
            - Capital and operating costs for SS, L2 and L3 upgrades
            - Bounds of TIN removal by SS, L2 and L3 upgrades

        Function calculates the capex, opex, and bounds parameters for L2upg3 
        based on L2 and L3 values
        
        Returns a dataframe with WWTP as index
        '''


        # read csv file
        df = pd.read_csv(self.WWTP_data_path)
        df.index = df['Abbreviation']    

        
        # Create index for WWTP
        self.WWTP = df.index


        # Create index for upgrades
        self.L = ['SS', 'L2', 'L3', 'L2upg3']                     # index for number of upgrades

        ## Add data for L2upg3
        for i in df.index:
            for j in [0,1]:
                df.loc[i, self.opex_L2upg3_tag[j]] = df.loc[i, self.opex_L3_tag[j]]
                df.loc[i, self.capex_L2upg3_tag[j]] = df.loc[i, self.capex_L3_tag[j]]
                df.loc[i, self.capex_L2upg3_power_tag[j]] = df.loc[i, self.capex_L3_power_tag[j]]
                df.loc[i, self.bounds_L2upg3_tag[j]] = df.loc[i, self.bounds_L3_tag[j]]                                      
                df.loc[i, self.bounds_L2upg3_max_tag[j]] = df.loc[i, self.bounds_L3_max_tag[j]]                              
        return df
    
    
    
    def calculate_opex(self, model):
        """
        Calculate the operating cost of the upgrades
        Units: mil USD (NPV)
        """
        
        #model.opex = Var(model.WWTP, model.L, model.t, initialize=0, bounds=(0, None))
        model.opex_monthly = Var(model.WWTP, model.L, model.t, initialize=0, bounds=(0, None))
        model.opex_yearly_NPV = Var(model.WWTP, model.L, model.t, initialize=0)
        model.opex_NPV = Var(model.WWTP, model.L, initialize=0)
        
        def opex_monthly_cond(model, WWTP, L, t):
            return model.opex_monthly[WWTP, L,t] == (
                model.status[WWTP,L,t] * 
                (model.A[WWTP,L] * model.x[WWTP,L,t] + model.B[WWTP,L])
                )
    
        def opex_yearly_NPV_cond(model, WWTP, L, years):
            
            year = self.datetime_years[years].year
            ind_start = np.where(self.datetime.year == year)[0][0]
            ind_end = np.where(self.datetime.year == year)[0][-1]
        
            return model.opex_yearly_NPV[WWTP, L, years] == sum(model.opex_monthly[WWTP,L,t] for t in range(ind_start,ind_end + 1)) / (1+self.discount_rate)**years
        
        def opex_NPV_cond(model, WWTP, L):
            return model.opex_NPV[WWTP, L] == sum(model.opex_yearly_NPV[WWTP, L,year] for year in model.years)
        
        
        self.interest = (1 + self.discount_rate)**(1/12) - 1    #monthly interest rate
        def opex_naive(model,WWTP,L):
            return model.opex_NPV[WWTP, L] == sum(model.opex_monthly[WWTP,L,t]/ (1+self.interest)**t for t in model.t)
            


        model.opex_monthly_cond = Constraint(model.WWTP, model.L, model.t, rule=opex_monthly_cond)   
        model.opex_yearly_NPV_cond = Constraint(model.WWTP, model.L, model.years, rule=opex_yearly_NPV_cond)
        model.opex_NPV_cond = Constraint(model.WWTP, model.L, rule=opex_NPV_cond)   
        
        return model

    def calculate_capex(self, model):
        """
        Add capital cost of the upgrades
        Units: mil USD (not adjusted for NPV)
        """
        
        model.capex_monthly = Var(model.WWTP, model.L, model.t, initialize=0, bounds=(0, None))
        model.capex_yearly_NPV = Var(model.WWTP, model.L, model.t, initialize=0)
        model.capex_NPV = Var(model.WWTP, model.L, initialize=0)
        
        def capex_monthly_cond_linear(model, WWTP, L, t):
            if L == 'L2upg3':
                return model.capex_monthly[WWTP, 'L2upg3',t] == (
                    model.u[WWTP,'L2upg3',t] * 
                    ((model.D[WWTP,'L2upg3'] * model.x_max[WWTP,'L2upg3'] + model.E[WWTP,'L2upg3']) - 
                    (model.D[WWTP,'L2'] * model.x_max[WWTP,'L2'] + model.E[WWTP,'L2']))
                    )
            else:
                return model.capex_monthly[WWTP, L, t] == (
                    model.u[WWTP,L,t] * 
                    (model.D[WWTP,L] * model.x_max[WWTP,L] + model.E[WWTP,L])
                    )
        
        def capex_monthly_cond_power(model, WWTP, L, t):
            if L == 'L2upg3':
                return model.capex_monthly[WWTP, 'L2upg3',t] == (
                    model.u[WWTP,'L2upg3',t] * 
                    ((model.alpha[WWTP,'L2upg3'] * model.x_max[WWTP,'L2upg3']**model.beta[WWTP,'L2upg3']) -
                    (model.alpha[WWTP,'L2'] * model.x_max[WWTP,'L2']**model.beta[WWTP,'L2']))
                    )
            else:
                return model.capex_monthly[WWTP, L, t] == (
                    model.u[WWTP,L,t] * 
                    (model.alpha[WWTP,L] * model.x_max[WWTP,L]**model.beta[WWTP,L])
                    )
        
        def capex_yearly_NPV_cond(model, WWTP, L, years):
            year = self.datetime_years[years].year
            ind_start = np.where(self.datetime.year == year)[0][0]
            ind_end = np.where(self.datetime.year == year)[0][-1]
        
            return model.capex_yearly_NPV[WWTP, L, years] == sum(model.capex_monthly[WWTP,L,t] for t in range(ind_start,ind_end + 1)) / (1+self.discount_rate)**years
        
        
        def capex_NPV_cond(model, WWTP, L):
            return model.capex_NPV[WWTP, L] == sum(model.capex_yearly_NPV[WWTP, L,year] for year in model.years)
        

        
        
        # check that self.capex_costing_linear is not an empty list
        if self.capex_costing_linear is not None and len(self.capex_costing_linear) > 0:
            print('Assuming linear capital cost for upgrades:', self.capex_costing_linear)
            model.capex_monthly_cond_linear = Constraint(model.WWTP, self.capex_costing_linear, model.t, rule=capex_monthly_cond_linear)   
        if self.capex_costing_power is not None and len(self.capex_costing_power) > 0:
            print('Assuming power law capital cost for upgrades:', self.capex_costing_power)
            model.capex_monthly_cond_power = Constraint(model.WWTP, self.capex_costing_power, model.t, rule=capex_monthly_cond_power)
        
        model.capex_yearly_NPV_cond = Constraint(model.WWTP, model.L, model.years, rule=capex_yearly_NPV_cond)
        model.capex_NPV_cond = Constraint(model.WWTP, model.L, rule=capex_NPV_cond)      
        
        return model

    
    def calculate_total_cost(self, model):
        """
        Add capital cost of the upgrades
        Units: mil USD (not adjusted for NPV)
        """
        
        model.total_cost_WWTP = Var(model.WWTP, initialize=0)
        model.total_cost = Var(initialize=0)
        
        def total_cost_WWTP(model, WWTP):
                return model.total_cost_WWTP[WWTP] == sum(model.capex_NPV[WWTP, L] + model.opex_NPV[WWTP, L]for L in model.L)
        
        model.total_cost_WWTP_cond = Constraint(model.WWTP, rule=total_cost_WWTP)   

        def total_cost(model):
                return model.total_cost == sum(model.total_cost_WWTP[WWTP] for WWTP in model.WWTP)
        
        model.total_cost_cond = Constraint(rule=total_cost)   
        
        return model
        



    # Function to calculate unit costs for each WWTP

    def compute_unit_costs_WWTP(self, model, solver):

        from itertools import combinations_with_replacement
        unit_cost_data = []
        
        unit_cost_dt =  pd.to_datetime(self.unit_cost_dt)
        t = np.where(self.datetime == unit_cost_dt)[0][0]
        
        tag = unit_cost_dt.strftime('%b') + '_' + str(unit_cost_dt.year)

        
        for combo in combinations_with_replacement(model.WWTP, 3):
            WWTP1, WWTP2, WWTP3 = combo
            
            model_2 = model.clone()  # Fast deep copy of the model

            if sum(value(model.b[WWTP1, ll, t]) for ll in model.L) == 0:
                print('Skipping', WWTP1, 'at t=', t, 'because it is not built')
                continue
            if sum(value(model.b[WWTP2, ll, t]) for ll in model.L) == 0:
                print('Skipping', WWTP2, 'at t=', t, 'because it is not built')
                continue
            if sum(value(model.b[WWTP3, ll, t]) for ll in model.L) == 0:
                print('Skipping', WWTP3, 'at t=', t, 'because it is not built')
                continue
            # conditions to save time:
            if (WWTP1 == 'Palo Alto') and (WWTP2 == 'SJSC') and (WWTP3 == 'SJSC'):
                continue

            if (WWTP1 == 'SJSC') and (WWTP2 == 'Sunnyvale') and (WWTP3 == 'Sunnyvale'):
                continue

            if (WWTP1 == 'Palo Alto') and (WWTP2 == 'Sunnyvale') and (WWTP3 == 'Sunnyvale'):
                continue



            for ww in model_2.WWTP:
                #print('Checking WWTP:',ww , 'compared to', WWTP1, WWTP2, WWTP3)
                if (ww != WWTP1) and (ww != WWTP2) and (ww != WWTP3):
                    #print('Forcing shutdown in:', ww)
                    for ll in model_2.L: 
                        if value(model.b[ww, ll, t]) == 1:
                            #print('Fixing status of', ww, ll, 'to 0')
                            model_2.status[ww, ll, t].fix(0)
                

            # set all dis_minus_reg to 0
            for ww in model_2.WWTP:
                if ww != WWTP1:
                    model_2.dis_minus_reg[ww, t] = 0
            
            print('Computing unit costs for', WWTP1, 'with', WWTP2, 'and', WWTP3, 'at t=', t)
                                        
            
            
                    
                    
            # loop over changes in removal requirements
            max_reg = sum(value(model.dis_minus_reg[WWTP, t]) for WWTP in model.WWTP)
            max_reg = 14000

            for reg in np.linspace(1, max_reg, 500):
                # Fix the required removal to the current value
                model_2.dis_minus_reg[WWTP1, t] =  reg

                # Run simulation and calculate the opex of the WWTP
                results_WWTP = solver.solve(model_2, tee=False)
                if results_WWTP.solver.termination_condition != TerminationCondition.optimal:
                    print(f"Solver did not find an optimal solution for {WWTP1} and {WWTP2} and {WWTP3} for t={t} and required removal={reg}.")
                    break
                
                opex_WWTP = sum(value(model_2.opex_monthly[WWTP1, L, t]) for L in model_2.L)
                opex_WWTP2 = sum(value(model_2.opex_monthly[WWTP2, L2, t]) for L2 in model_2.L)
                opex_WWTP3 = sum(value(model_2.opex_monthly[WWTP3, L3, t]) for L3 in model_2.L)
                opex_total = sum(value(model_2.opex_monthly[ww, ll, t]) for ww in model_2.WWTP for ll in model_2.L)
                
                # Find L
                
                L1 = []
                L2 = []
                L3 = []
                
                for L in model_2.L:
                    if value(model_2.status[WWTP1, L, t]) > 0:
                        L1.append(L)
                    if value(model_2.status[WWTP2, L, t]) > 0:
                        L2.append(L)
                    if value(model_2.status[WWTP3, L, t]) > 0:
                        L3.append(L)
                    
            
                r_total_new = sum(model_2.r[WWTP2, t].value for WWTP2 in model_2.WWTP)

                unit_cost_data.append({
                    'WWTP': WWTP1,
                    'WWTP2': WWTP2,
                    'WWTP3': WWTP3,
                    'L1': L1,
                    'L2': L2,
                    'L3': L3,
                    't': t,
                    'datetime': self.datetime[t],
                    'Additional_removal': reg,
                    'Required_removal': sum(model.dis_minus_reg[WWTP, t].value for WWTP in model_2.WWTP),
                    'Opex_1': opex_WWTP,
                    'Opex_2': opex_WWTP2,
                    'Opex_3': opex_WWTP3,
                    'Opex_total_new': opex_total,
                    'r_total_new': r_total_new,
                })
            
            
     
        df = pd.DataFrame(unit_cost_data)
        df.to_csv(self.figpath_base + f"unit_cost_{tag}.csv", index=False)
    
    


if __name__ == "__main__":
    # import flexparams.json
    # basepath = "CapExpParams.json"   

    basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
    fp = os.path.join(os.getcwd(),basepath)     
    params = json.load(open(fp))

    # Define constraint tag based on the model type
    if params['trading_market'] and params['joint_infrastructure']:
        params['Constraint_tag'] = 'Full_coordination'
    elif params['trading_market']:
        params['Constraint_tag'] = 'Partial_coordination'
        if params['seasonal_regulation']:
            params['figpath_capex'] = 'Results/' + params['version_num'] + "/Seasonal/" + 'No_coordination' + "/"
            params['figpath_opex_partial'] = 'Results/' + params['version_num'] + "/Seasonal/" + 'Partial_coordination' + "/"
        else:
            params['figpath_capex'] = 'Results/' + params['version_num'] + "/Year_round/" + 'No_coordination' + "/"
            params['figpath_opex_partial'] = 'Results/' + params['version_num'] + "/Year_round/" + 'Partial_coordination' + "/"
    else:
        params['Constraint_tag'] = 'No_coordination'
    

    # Define folder names for sensitivity analysis runs

    if params['sensitivity_analysis']:
        mult = params['projection_multiplier']
        
        if not os.path.exists('Sensitivity/'):
            os.makedirs('Sensitivity/')

        if params['seasonal_regulation']:
            params['figpath'] = 'Sensitivity/' + params['version_num'] + "/Seasonal/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
            params['figpath_base'] = 'Sensitivity/' + params['version_num'] + "/Seasonal/" + params['Constraint_tag'] + "_" + str(mult) + "_" 
        else:
            params['figpath'] = 'Sensitivity/' + params['version_num'] + "/Year_round/" + params['Constraint_tag'] + "/"  + str(mult) + "/" 
            params['figpath_base'] = 'Sensitivity/' + params['version_num'] + "/Year_round/" + params['Constraint_tag'] + "_" + str(mult) + "_" 
    
    else:        
        if params['seasonal_regulation']:
            params['figpath'] = 'Results/' + params['version_num'] + "/Seasonal/" + params['Constraint_tag'] + "/"
            params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] + "_Seasonal_" 
        else:
            params['figpath'] = 'Results/' + params['version_num'] + "/Year_round/" + params['Constraint_tag'] + "/"
            params['figpath_base'] = 'Results/' + params['version_num'] + "/" + params['Constraint_tag'] + "_YearRound_" 

    
    if not os.path.exists(params['figpath']):
        os.makedirs(params['figpath'])
    
    
    # create multiperiodRO object
    m = capacity_expansion(params)


 
    model = m.main()

    