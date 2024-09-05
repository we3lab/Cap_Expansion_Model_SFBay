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
from matplotlib import pyplot as plt 
import os, json, warnings
from pyomo.environ import *


class capacity_expansion():
    def __init__(self, params):
        for k, v in params.items():
            setattr(self, k, v)
        
        # set up time periods of model
        self.datetime = pd.date_range(start=self.start_date, periods = 12*self.total_years, freq=self.timestep_freq)
        self.datetime_years = pd.date_range(start=self.start_date, periods = self.total_years, freq='YE')

    
    
    def main(self):
        """
        Run the model.
            - 
            -
            -
            -
        """
        model = self.build()

        '''
        # Solve MILP with gurobi
        solver = SolverFactory('gurobi')
        solver.solve(model, tee=True)
        '''    

        # Solve LP with ipopt
        #solver = SolverFactory('ipopt')
        
        
        #'''
        # Solve with MindtPy
        solver = SolverFactory('mindtpy')
        solver.solve(model, 
                     mip_solver = 'gurobi',
                     nlp_solver = 'ipopt',
                     tee=True)
        #'''
        
        #solver.solve(model)

        print('Policy Scenario:', self.Constraint_tag)
        print('Total NPV Cost = ', round(model.total_cost(),2), 'million')
        
        for WWTP in model.WWTP:
            print('WWTP: ', WWTP, '(Total Cost:', round(model.total_cost_WWTP[WWTP](),2), 'million)')
            for L in model.L:
                if sum(model.u[WWTP,L,t].value for t in model.t) == 1:
                    print('\t',L+':', round(model.x_max[WWTP,L](),2),'; Lower bound (' + str(model.LB[WWTP, L].value)+ '); Capex:',round(model.capex_NPV[WWTP,L](),2), '; Opex:', round(model.opex_NPV[WWTP,L](),2))
                else:
                    print('\t',L+': not built', round(model.capex_NPV[WWTP,L](),2))
        
        #solver.options['ResultFile'] = "test.ilp"
        
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
        model.L = ['SS', 'L2', 'L2pt5', 'L3']                      # number of upgrades
        model.years = range(self.total_years)

        
        model.DualReductions = 0
        
        # Add parameters
        model = self.add_regulation_params(model, df)
        model = self.add_upgrade_bounds(model, df)
        model = self.add_capex_params(model, df)
        model = self.add_opex_params(model, df)

        # Add variables
        model = self.add_upgrade_variables(model)
        model = self.add_integer_variables(model)
        model = self.set_integer_variables(model)
        
        
        # Add constraints
        model = self.add_capacity_constraints(model)
        model = self.add_regulatory_constraints(model, self.Constraint_tag)
        model = self.add_max_capacity_constraints(model)
        model = self.add_build_upgrade_constraint(model)
        model = self.add_integer_constraints(model)
        

        
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
        upgrade_bound_tags = {'SS': self.bounds_SS_tag, 'L2': self.bounds_L2_tag, 'L2pt5': self.bounds_L2pt5_tag, 'L3': self.bounds_L3_tag}
        
        
        LB = {(i, upgrade): df.loc[i, upgrade_bound_tags[upgrade][0]] for upgrade in self.L for i in self.WWTP}
        UB = {(i, upgrade): df.loc[i, upgrade_bound_tags[upgrade][1]] for upgrade in self.L for i in self.WWTP}
        
        model.UB = Param(model.WWTP, model.L, initialize=UB, mutable=True)
        model.LB = Param(model.WWTP, model.L, initialize=LB, mutable=True)

        return model


    def add_upgrade_variables(self, model):
        """
        Variable for the amount of nutrient removed 
        by each upgrade for each WWTP
        """
        
        def fb(model, WWTP, L, t):
            return (model.LB[WWTP, L], model.UB[WWTP, L])
        
        def fb_max(model, WWTP, L):
            return (model.LB[WWTP, L], model.UB[WWTP, L])
        
        def x_init(model, WWTP, L, t):
            return model.LB[WWTP, L]
        
        def x_max_init(model, WWTP, L):
            return model.LB[WWTP, L]

        model.x = Var(model.WWTP, model.L, model.t, bounds=fb, initialize=x_init)    # total nitrogen removed by each facility at each timestep

        model.x_max = Var(model.WWTP, model.L, bounds=fb_max, initialize=x_max_init)    # Mmaximum nitrogen removed by each facility by each upgrade
        

        model.r = Var(model.WWTP, model.t, initialize=0)                      # total nitrogen removed by each facility at each timestep

        return model
    
    
    def add_capex_params(self, model, df):
        '''
        Capital cost estimates for each upgrade
        based on the BACWA 2017 Report
        '''
        
        #tags
        capex_tags = {'SS': self.capex_SS_tag, 'L2': self.capex_L2_tag, 'L2pt5': self.capex_L2pt5_tag, 'L3': self.capex_L3_tag}    

        # capital cost (D*x + E)
        model.D = {(i, upgrade) : df.loc[i, capex_tags[upgrade][0]] for upgrade in self.L for i in self.WWTP}
        model.E = {(i, upgrade) : df.loc[i, capex_tags[upgrade][1]] for upgrade in self.L for i in self.WWTP}

        return model
    

    def add_opex_params(self, model, df):
        '''
        Capital cost estimates for each upgrade
        based on the BACWA 2017 Report
        Opex reported as mil $/year
        Tag will be divided by 12 to reflect monthly costs
        '''
        opex_tags = {'SS': self.opex_SS_tag, 'L2': self.opex_L2_tag, 'L2pt5': self.opex_L2pt5_tag, 'L3': self.opex_L3_tag} 


        # operating cost (A*x + B) per month 
        model.A = {(i, upgrade) : df.loc[i, opex_tags[upgrade][0]]/12 for upgrade in self.L for i in self.WWTP}
        model.B = {(i, upgrade) : df.loc[i, opex_tags[upgrade][1]]/12 for upgrade in self.L for i in self.WWTP}

        return model


    def add_integer_variables(self, model):
        """
        Add integer variable that determines if an upgrade is built
        """

        model.eps = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that determines if an upgrade is operated')
        #model.eps_max = Var(model.WWTP, model.L, within=Binary, initialize=0, doc='Binary variable that determines if an upgrade is built')

        model.u = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that determines when an upgrade starts being built')
        #model.zeta = Var(model.WWTP, model.L, model.t, within=Binary, initialize=0, doc='Binary variable that determines when an upgrade build is completed')
        
        return model


    def set_integer_variables(self,model):
        """
        Set integer variables for opex only model
        LP_model
        """

        model.eps.fix(0)
        #model.eps_max.fix(0)
        model.u.fix(0)
        #model.zeta.fix(0)
        

        if self.include_L3:
            model.eps[:,'L3',:].unfix()
            #model.eps_max[:,'L3'].unfix()
            model.u[:,'L3',:].unfix()
            #model.zeta[:,'L3',:].unfix()
        
        if self.include_L2:
            model.eps[:,'L2',:].unfix()
            #model.eps_max[:,'L2'].unfix()
            model.u[:,'L2',:].unfix()
            #model.zeta[:,'L2',:].unfix()
        
        if self.include_L2pt5:
            model.eps[:,'L2pt5',:].unfix()
            #model.eps_max[:,'L2pt5'].unfix()
            model.u[:,'L2pt5',:].unfix()
            #model.zeta[:,'L2pt5',:].unfix()
        
        if self.include_SS:
            model.eps[:,'SS',:].unfix()
            #model.eps_max[:,'SS'].unfix()
            model.u[:,'SS',:].unfix()
            #model.zeta[:,'SS',:].unfix()
        
        # Fix initial eps at 0
        model.eps[:,:,0].fix(0)

        return model


    def add_regulation_params(self, model, df):
        """
        Add regulatory parameters to the model
        based on current discharge of each WWTP
        and regulations from Water Board SF Bay 2024.

        Current discharge: BACWA 2023 Report Table 1-3"Current Flow and Nutrient Discharge Levels to the Bay (10/2016 - 9/2019) in kg/day"
        
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
            current = df.loc[i, self.discharge_current_tag]                            # kg/day
            projected = df.loc[i, self.discharge_projected_tag]*0.453592               # convert lbs to kg 
            discharge[i] = np.linspace(current, projected, 
                                            len(self.datetime), endpoint=True) 
        # regulations for each WWTP
        regulations = pd.DataFrame(index=self.datetime, columns=df.index)
        for i in model.WWTP:
            regulations.loc[:, i] = df.loc[i, self.reg_current_tag]
            regulations.loc[self.datetime >= self.new_reg_year, i] = df.loc[i, self.reg_projected_tag]
            if self.seasonal_regulation:
                regulations.loc[self.datetime.month.isin([1,2,3,4,10,11,12]), i] = 100000


        reg_dict = {(WWTP,t): regulations[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        dis_dict = {(WWTP,t): discharge[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        dis_minus_reg_dict = {(WWTP,t): discharge[WWTP].iloc[t]-regulations[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        
        model.reg = Param(model.WWTP, model.t, initialize=reg_dict, mutable=True)
        model.dis = Param(model.WWTP, model.t, initialize=dis_dict, mutable=True)
        model.dis_minus_reg = Param(model.WWTP, model.t, initialize=dis_minus_reg_dict, mutable=True)

        return model


    def add_integer_constraints(self, model):
        """
        Add integer constraints to the model
        Constraints are:
            1) You can't operate L2 and L3 at the same time
            2) You have to build L2 before upgrading to L2.5
            3) You can't operate L2.5 and L3 at the same time
        """

        # Constraint that you can't operate L2 and L3 at the same time
        def L2_L3_constraint(model, WWTP, t):
            return model.eps[WWTP,'L3',t] <= 1 - model.eps[WWTP,'L2',t]
        model.integer_constraint_L3 = Constraint(model.WWTP, model.t, rule=L2_L3_constraint)

        # Constraint that you have to build L2 before upgrading to L2.5
        def L2_L2pt5_constraint(model, WWTP, t):
            return model.eps[WWTP,'L2pt5',t] <= model.eps[WWTP,'L2',t]
        model.integer_constraint_L2pt5 = Constraint(model.WWTP, model.t, rule=L2_L2pt5_constraint)

        # Constraint that L2 has to operate at max capacity while operating L2.5
        def L2pt5_max_constraint(model, WWTP, t):
            return model.x[WWTP,'L2',t] >= model.eps[WWTP,'L2pt5',t]* model.UB[WWTP, 'L2']
        model.integer_constraint_L2pt5_max = Constraint(model.WWTP, model.t, rule=L2pt5_max_constraint)

        # Constraint that you can't operate L2.5 and L3 at the same time
        def L2pt5_L3_constraint(model, WWTP, t):
            return model.eps[WWTP,'L3',t] <= 1 - model.eps[WWTP,'L2pt5',t]
        model.integer_constraint_L2pt5L3 = Constraint(model.WWTP, model.t, rule=L2pt5_L3_constraint)


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
                sum(model.eps[WWTP,L,t] * model.x[WWTP,L,t]for L in model.L)
            )
        model.current_capacity = Constraint(model.WWTP, model.t, rule=current_capacity)

        return model

    
    def add_regulatory_constraints(self, model, Constraint_tag):
        """
        Add Constraints to the model based on discharge and regulation type
        Two regulations are possible based on Constraint_tag:
            1) Individual: Total discharge by each WWTP must be less than WWTP regulation
            2) Subembayment: Total removal by all WWTPs should be less than the sum of combined WWTP discharge regulation
        """
        
        if Constraint_tag == 'Individual':
        # Constraint that the total WWTP discharge must be less than the WWTP regulation
            def regulation(model, WWTP, t):
                return model.r[WWTP,t] >= model.dis_minus_reg[WWTP,t]
            model.regulation = Constraint(model.WWTP, model.t, rule=regulation)

        if Constraint_tag == 'Subembayment':
        # Constraint that the total WWTP discharge by all WWTP in the subembayment must be less than the sum of WWTP regulations
            def regulation(model, t):
                return sum(model.r[WWTP,t] for WWTP in model.WWTP) >= sum(model.dis_minus_reg[WWTP,t] for WWTP in model.WWTP)
            model.regulation = Constraint(model.t, rule=regulation)

        return model


    def add_build_upgrade_constraint(self, model):
        """
        Binary variable to determine if the NMS is built
        """

        self.time_to_build = 12*3       #three years to build
                
        # Constraint that u has to be greater than eps (1 when built)
        def find_u(model, WWTP, L, t):
            if t == 0:
                return model.u[WWTP, L,t] == 0
            else:
                return model.u[WWTP, L,t] == model.eps[WWTP,L,t] - model.eps[WWTP,L,t-1]
        
        model.find_u = Constraint(model.WWTP, model.L, model.t, rule=find_u)

        """ 
        def time_to_build(model,WWTP,L,t):
            if t == 0:
                return model.zeta[WWTP,L,t] == 0
            else:
                for t in range(self.time_to_build):
                    return model.zeta[WWTP,L,t+1] == model.eps[WWTP,L,t]
                    

        model.time_to_build = Constraint(model.WWTP, model.L, model.t, rule=time_to_build)
        
        """
        
        return model
    
    
    
    def add_max_capacity_constraints(self, model):
        """
        Get the maximum amount of nutrients removed to calculate
        the capital cost of infrastructure
        """
        
        # Constraint that max removal has to be greater than current removal
        def max_capacity(model, WWTP, L, t):
            return model.x_max[WWTP, L] >= model.x[WWTP,L,t]
        
        # Constraint that eps_max has to be greater than eps (1 if built and 0 if not built)
        def max_built(model, WWTP, L, t):
            return model.eps_max[WWTP, L] >= model.eps[WWTP,L,t]


        

        model.max_capacity = Constraint(model.WWTP, model.L, model.t, rule=max_capacity)
        #model.max_built = Constraint(model.WWTP, model.L, model.t, rule=max_built)

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

        Function calculates the capex, opex, and bounds parameters for L2.5 
        based on L2 and L3 values
        
        Returns a dataframe with WWTP as index
        '''


        # read csv file
        df = pd.read_csv(self.WWTP_data_path)
        df.index = df['Abbreviation']    

        
        # Create index for WWTP
        self.WWTP = df.index


        # Create index for upgrades
        self.L = ['SS', 'L2', 'L3', 'L2pt5']                     # index for number of upgrades

        ## Add data for L2pt5
        for i in df.index:
            for j in [0,1]:
                df[self.opex_L2pt5_tag[j]] = df[self.opex_L3_tag[j]] - df[self.opex_L2_tag[j]]
                df[self.capex_L2pt5_tag[j]] = df[self.capex_L3_tag[j]] - df[self.capex_L2_tag[j]]
                df[self.bounds_L2pt5_tag[j]] = df[self.bounds_L3_tag[j]] - df[self.bounds_L2_tag[j]]
        
        
        return df
    
    
    
    def calculate_opex(self, model):
        """
        Calculate the operating cost of the upgrades
        Units: mil USD (NPV)
        """
        self.interest = (1 + self.discount_rate)**(1/12) - 1    #monthly interest rate
        
        #model.opex = Var(model.WWTP, model.L, model.t, initialize=0, bounds=(0, None))
        model.opex_monthly = Var(model.WWTP, model.L, model.t, initialize=0, bounds=(0, None))
        model.opex_yearly_NPV = Var(model.WWTP, model.L, model.t, initialize=0)
        model.opex_NPV = Var(model.WWTP, model.L)
        
        def opex_monthly_cond(model, WWTP, L, t):
            if L == 'L2pt5':
                return model.opex_monthly[WWTP, 'L2pt5',t] == (
                    model.eps[WWTP,'L2pt5',t] * 
                    (model.A[WWTP,'L2pt5'] * model.x[WWTP,'L2',t] + model.A[WWTP,'L3']* model.x[WWTP, 'L2pt5',t] + model.B[WWTP,'L2pt5'])
                    )
            else:
                return model.opex_monthly[WWTP, L,t] == (
                    model.eps[WWTP,L,t] * 
                    (model.A[WWTP,L] * model.x[WWTP,L,t] + model.B[WWTP,L])
                    )
        
        def opex_yearly_NPV_cond(model, WWTP, L, years):
            month_start = 12*(years)
            month_end = 12*(years+1)
            return model.opex_yearly_NPV[WWTP, L, years] == sum(model.opex_monthly[WWTP,L,t] for t in range(month_start,month_end)) / (1+self.discount_rate)**years
        
        def opex_NPV_cond(model, WWTP, L):
            return model.opex_NPV[WWTP, L] == sum(model.opex_yearly_NPV[WWTP, L,year] for year in model.years)
        
        def opex_naive(model,WWTP,L):
            return model.opex_NPV[WWTP, L] == sum(model.opex_monthly[WWTP,L,t]/ (1+self.interest)**t for t in model.t)
            


        model.opex_monthly_cond = Constraint(model.WWTP, model.L, model.t, rule=opex_monthly_cond)   
        model.opex_yearly_NPV_cond = Constraint(model.WWTP, model.L, model.years, rule=opex_yearly_NPV_cond)
        model.opex_NPV_cond = Constraint(model.WWTP, model.L, rule=opex_NPV_cond)   
        #model.opex_NPV_cond = Constraint(model.WWTP, model.L, rule=opex_naive)   
        
        return model

    def calculate_capex(self, model):
        """
        Add capital cost of the upgrades
        Units: mil USD (not adjusted for NPV)
        """
        
        model.capex_monthly = Var(model.WWTP, model.L, model.t, initialize=0, bounds=(0, None))
        model.capex_yearly_NPV = Var(model.WWTP, model.L, model.t, initialize=0)
        model.capex_NPV = Var(model.WWTP, model.L, initialize=0)
        
        def capex_monthly_cond(model, WWTP, L, t):
            if L == 'L2pt5':
                return model.capex_monthly[WWTP, 'L2pt5',t] == (
                    model.u[WWTP,'L2pt5',t] * 
                    (model.D[WWTP,'L2pt5'] * model.x_max[WWTP,'L2'] + model.D[WWTP,'L3']* model.x_max[WWTP, 'L2pt5'] + model.E[WWTP,'L2pt5'])
                    )
            else:
                return model.capex_monthly[WWTP, L, t] == (
                    model.u[WWTP,L,t] * 
                    (model.D[WWTP,L] * model.x_max[WWTP,L] + model.E[WWTP,L])
                    )
        
        def capex_yearly_NPV_cond(model, WWTP, L, years):
            month_start = 12*(years)
            month_end = 12*(years+1)
            return model.capex_yearly_NPV[WWTP, L, years] == sum(model.capex_monthly[WWTP,L,t] for t in range(month_start,month_end)) / (1+self.discount_rate)**years
        
        
        def capex_NPV_cond(model, WWTP, L):
            return model.capex_NPV[WWTP, L] == sum(model.capex_yearly_NPV[WWTP, L,year] for year in model.years)
        

        
        model.capex_monthly_cond = Constraint(model.WWTP, model.L, model.t, rule=capex_monthly_cond)   
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
        
    
    # Plotting functions
    def plot_regulations(self, model):
        
        fig, ax = plt.subplots()
        color_list = ['blue', 'red', 'green']
        colors = {WWTP: color_list[WWTP] for WWTP in model.WWTP}

        # plot regulations as dashed lines
        for WWTP in model.WWTP:
            plt.plot(self.datetime, [model.dis[WWTP, t] for t in model.t], '-', color=colors[WWTP])
            plt.plot(self.datetime, [model.reg[WWTP, t] for t in model.t], '--', color=colors[WWTP])
        plt.xlabel('Year')
        plt.ylabel('TIN Discharge (Kg N/day)')
        plt.show()
        fig.savefig("regulation.png")

        return fig, ax
    
    def plot_discharge_post_individual(self, model):
        
        colors = {'L3':'black', 'L2':'red', 'L2pt5':'green', 'SS': 'pink'}
        
        for WWTP in model.WWTP:
            fig, ax1 = plt.subplots()
            
            for L in model.L:
                if model.eps[WWTP,L,299]() == 1:
                    ax1.plot(self.datetime, [model.x[WWTP,L,t]()*model.eps[WWTP,L,t]() for t in model.t], '-', color = colors[L],label = 'Quantity removed with ' + L)

            ax1.plot(self.datetime, [model.r[WWTP,t]() for t in model.t], '-', color='orange', label = 'Total quantity removed')
            ax1.plot(self.datetime, [value(model.dis_minus_reg[WWTP,t]) for t in model.t],  '--', color='blue', label = 'Required TIN removal', alpha=0.5)

            if self.seasonal_regulation:
                ax1.set_ylim(-500, round(max([value(model.dis_minus_reg[WWTP,t]) for t in model.t])+100, -1))
            plt.legend(loc='upper left')
            plt.xlabel('Year')
            plt.ylabel('TIN removed (Kg N/day)')
            plt.title(WWTP)
            plt.show()
        #fig.savefig("discharge_post.png")

        return fig, ax1

    def plot_discharge_post_subembayment(self, model):

        
        fig, ax1 = plt.subplots()
        
        colors = ['green', 'red', 'purple', 'black', 'yellow', 'pink', 'brown', 'grey']
        
        for i, WWTP in enumerate(model.WWTP):
            ax1.plot(self.datetime, [model.r[WWTP,t]() for t in model.t], '-', color=colors[i] , label = WWTP)
        
        ax1.plot(self.datetime, [sum(model.r[WWTP,t]() for WWTP in model.WWTP) for t in model.t], '-', color='orange', label = 'Total quantity removed')
        ax1.plot(self.datetime, [sum(model.dis_minus_reg[WWTP,t].value for WWTP in model.WWTP) for t in model.t] , '--', color='blue', label = 'Required TIN removal', alpha=0.5)
        

        if self.seasonal_regulation:
            ax1.set_ylim(-500, round(max([sum(model.dis_minus_reg[WWTP,t].value for WWTP in model.WWTP) for t in model.t])+100, -1))
            
        plt.legend()
        plt.xlabel('Year')
        plt.ylabel('TIN removed (Kg N/day)')
        plt.show()
        #fig.savefig("discharge_post.png")

        return fig, ax1
    
    def plot_subfigures(self, model, plot_tag):

        fig, axs = plt.subplots(len(model.WWTP), 1, figsize=(10, 5))

        colors = {'L3':'black', 'L2':'red', 'L2pt5':'green', 'SS': 'pink'}
        
        ciel = -(len(model.WWTP)//-2)-1
        for i, WWTP in enumerate(model.WWTP):
            for L in model.L:
                if plot_tag == 'eps':
                    axs[i].plot(self.datetime, [model.eps[WWTP,L,t]() for t in model.t], '-', color = colors[L],label = L)
                    axs[i].set_yticks([0,1])
                if plot_tag == 'x':
                    axs[i].plot(self.datetime, [model.x[WWTP,L,t]() for t in model.t], '-', color = colors[L],label = L)
                if plot_tag == 'x_eps':
                    axs[i].plot(self.datetime, [model.x[WWTP,L,t]()*model.eps[WWTP,L,t]() for t in model.t], '-', color = colors[L],label = L)
                    if i == ciel:
                        axs[i].set_ylabel('TIN (Kg N/day)')
                if plot_tag == 'opex':
                    axs[i].plot(self.datetime_years, [model.opex_yearly_NPV[WWTP,L,year]() for year in model.years], '-', color = colors[L],label = L) 
                    if i == ciel:
                        axs[i].set_ylabel('Opex (NPV $mil/year)')
                if plot_tag == 'capex':
                    axs[i].plot(self.datetime_years, [model.capex_yearly_NPV[WWTP,L,year]() for year in model.years], '-', color = colors[L],label = L)
                    if i == ciel:
                        axs[i].set_ylabel('Capex (mil $)')
                if plot_tag == 'u':
                    axs[i].plot(self.datetime, [model.u[WWTP,L,t]() for t in model.t], '-', color = colors[L],label = L)
                    axs[i].set_yticks([0,1])
            
            if plot_tag == 'opex':
                axs[i].plot(self.datetime_years, [sum(model.opex_yearly_NPV[WWTP,L,year]() for L in model.L) for year in model.years], '-', color = 'blue',label = 'Total Opex') 

            if plot_tag == 'capex':
                # plot cumulative capex_yearly_NPV
                cum_capex = []
                cum_capex_value = 0
                for year in model.years:
                    cum_capex_value += sum(model.capex_yearly_NPV[WWTP,L,year]() for L in model.L)
                    cum_capex.append(cum_capex_value)
                axs[i].plot(self.datetime_years, cum_capex, '-', color = 'blue',label = 'Cumulative capex')
            
            if i == ciel:
                axs[i].legend(loc='lower left')   
            axs[i].set_title(WWTP)
        
        fig.suptitle(plot_tag, fontsize=16)
        fig.tight_layout()    
        plt.show()
        return fig, axs
    
    


if __name__ == "__main__":
    # import flexparams.json
    # basepath = "CapExpParams.json"   

    basepath = "CapExpParams.json"    # use for running the script in jupyter notebook
    fp = os.path.join(os.getcwd(),basepath)     
    params = json.load(open(fp))
    # create multiperiodRO object
    m = capacity_expansion(params)

    #print('Details:')
    #print(m.__dict__)

    #fig, ax = m.plot_regulations(model)

    model = m.main()
    if m.Constraint_tag == 'Individual':
        fig, ax = m.plot_discharge_post_individual(model)
    
    if m.Constraint_tag == 'Subembayment':
        fig, ax = m.plot_discharge_post_subembayment(model)

    fig, ax = m.plot_subfigures(model, 'eps')
    fig, ax = m.plot_subfigures(model, 'x')
    fig, ax = m.plot_subfigures(model, 'x_eps')
    fig, ax = m.plot_subfigures(model, 'u')
    fig, ax = m.plot_subfigures(model, 'opex')
    fig, ax = m.plot_subfigures(model, 'capex')