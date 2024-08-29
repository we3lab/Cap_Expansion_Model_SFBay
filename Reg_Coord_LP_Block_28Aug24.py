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


    
    
    def main(self):
        """
        Run the model.
            - 
            -
            -
            -
        """
        model = self.build()


        solver = SolverFactory('ipopt')
        solver.solve(model, tee=True)

        print('Total Cost = ', model.value())
        opex = self.calculate_opex(model)
        capex = self.calculate_capex(model)
        
        for WWTP in model.WWTP:
            print('WWTP: ', WWTP)
            for L in model.L:
                if model.eps[WWTP,L, 299]() > 0.9:
                    print(L+':', round(model.x_max[WWTP,L](),2))
                else:
                    print(L+': not built')

        
        # calculate costs
        
        print('Opex:', opex)
        print('Capex:', capex)

        
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
        

        
        # Set objectives
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
        
        # create a nested dictionary with WWTP as outside key and upper/lower bound as inside key
        #LB = {i: {upgrade : df.loc[i, upgrade_bound_tags[upgrade][0]] for upgrade in self.L} for i in self.WWTP}
        #UB = {i: {upgrade : df.loc[i, upgrade_bound_tags[upgrade][1]] for upgrade in self.L} for i in self.WWTP}
        
        LB = {(i, upgrade): df.loc[i, upgrade_bound_tags[upgrade][0]] for upgrade in self.L for i in self.WWTP}
        UB = {(i, upgrade): df.loc[i, upgrade_bound_tags[upgrade][1]] for upgrade in self.L for i in self.WWTP}
        
        model.UB = Param(model.WWTP, model.L, initialize=UB)

        return model


    def add_upgrade_variables(self, model):
        """
        Variable for the amount of nutrient removed 
        by each upgrade for each WWTP
        """
        
        def fb(model, WWTP, L, t):
            #return (0, UB[WWTP][L])
            return (0, model.UB[WWTP, L])

        model.x = Var(model.WWTP, model.L, model.t, bounds=fb)    # total nitrogen removed by each facility at each timestep


        
        for WWTP in model.WWTP:
            if self.include_SS:
                model.x[WWTP,'SS',:].fix(UB[WWTP]['SS'])
            else:
                model.x[WWTP,'SS',:].fix(0)

        model.r = Var(model.WWTP, model.t)                      # total nitrogen removed by each facility at each timestep

        #print(model.x.display())
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

        model.eps = Var(model.WWTP, model.L, model.t, within=Binary)

        return model


    def set_integer_variables(self,model):
        """
        Set integer variables for opex only model
        LP_model
        """

        model.eps.fix(0)

        if self.include_L3:
            model.eps[:,'L3',:].fix(1)
        
        if self.include_L2:
            model.eps[:,'L2',:].fix(1)
        
        if self.include_L2pt5:
            model.eps[:,'L2pt5',:].fix(1)
        
        if self.include_SS:
            model.eps[:,'SS',:].fix(1)

        return model


    def add_regulation_params(self, model, df):
        """
        Add regulatory parameters to the model
        based on current discharge of each WWTP
        and regulations from Water Board SF Bay 2024.

        Current discharge: BACWA 2023 Report Table 1-3"Current Flow and Nutrient Discharge Levels to the Bay (10/2016 - 9/2019) in kg/day"
        Projected discharge: BACWA 2017 Report
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
                regulations.loc[self.datetime.month.isin([1,2,3,10,11,12]), i] = 100000


        reg_dict = {(WWTP,t): regulations[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        dis_dict = {(WWTP,t): discharge[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        dis_minus_reg_dict = {(WWTP,t): discharge[WWTP].iloc[t]-regulations[WWTP].iloc[t] for t in model.t for WWTP in self.WWTP}
        
        model.reg = Param(model.WWTP, model.t, initialize=reg_dict)
        model.dis = Param(model.WWTP, model.t, initialize=dis_dict)
        model.dis_minus_reg = Param(model.WWTP, model.t, initialize=dis_minus_reg_dict)

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

        # Constraint that you can't operate L2.5 and L3 at the same time
        def L2pt5_L3_constraint(model, WWTP, t):
            return model.eps[WWTP,'L3',t] <= 1 - model.eps[WWTP,'L2pt5',t]
        model.integer_constraint_L3 = Constraint(model.WWTP, model.t, rule=L2pt5_L3_constraint)


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


    def add_max_capacity_constraints(self, model):
        """
        Get the maximum amount of nutrients removed to calculate
        the capital cost of infrastructure
        """
        model.x_max = Var(model.WWTP, model.L)


        if not self.include_SS:
            model.x_max[:,'SS'].fix(0)
        
        # Constraint that max removal has to be greater than current removal
        def max_capacity(model, WWTP, L, t):
            return model.x_max[WWTP, L] >= model.x[WWTP,L,t]
        model.max_capacity = Constraint(model.WWTP, model.L, model.t, rule=max_capacity)     

        return model


    def add_objective(self, model, Objective_tag):
        """
        Add objective to model
        Define annual interest rate in json file
        Parameters for opex and capex based on add_opex and add_capex functions
        """

        model.int = (1 + self.interest_rate)**(1/12) - 1    #monthly interest rate
        
                
        # Select optimization
        def total_cost(model):
            return (
                #operating cost
                sum(model.eps[WWTP, 'L3', t] * (model.A[WWTP,'L3']* model.x[WWTP,'L3',t] + model.B[WWTP,'L3']) / (1+model.int)**t for t in model.t for WWTP in model.WWTP)
                + sum(model.eps[WWTP, 'L2',t] * (model.A[WWTP,'L2']* model.x[WWTP,'L2',t] + model.B[WWTP,'L2']) / (1+model.int)**t for t in model.t for WWTP in model.WWTP)
                + sum(model.eps[WWTP, 'SS',t] * (model.A[WWTP,'SS']* model.x[WWTP,'SS',t] + model.B[WWTP,'SS']) / (1+model.int)**t for t in model.t for WWTP in model.WWTP) 
                + sum(model.eps[WWTP, 'L2pt5',t] * (model.A[WWTP,'L2pt5']* model.x[WWTP,'L2',t] +  model.A[WWTP,'L3']* model.x[WWTP,'L2pt5',t] + model.B[WWTP,'L2pt5']) * (1+model.int)**t for t in model.t for WWTP in model.WWTP)

                # capital cost
                + sum(model.eps[WWTP,'L3',299] * (model.D[WWTP,'L3'] * model.x_max[WWTP, 'L3'] + model.E[WWTP,'L3']) for WWTP in model.WWTP)
                + sum(model.eps[WWTP,'L2',299] * (model.D[WWTP,'L2'] * model.x_max[WWTP, 'L2'] + model.E[WWTP,'L2']) for WWTP in model.WWTP)
                + sum(model.eps[WWTP,'SS',299] * (model.D[WWTP,'SS'] * model.x_max[WWTP, 'SS'] + model.E[WWTP,'SS'])for WWTP in model.WWTP) 
                + sum(model.eps[WWTP,'L2pt5',299] * (model.D[WWTP,'L2pt5'] * model.x_max[WWTP,'L2'] + model.D[WWTP,'L3']* model.x_max[WWTP, 'L2pt5'] + model.E[WWTP,'L2pt5']) for WWTP in model.WWTP)
                )

        model.value = Objective(rule=total_cost, sense=minimize)

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
        
        opex = {}
        for WWTP in model.WWTP:
            opex_val = 0
            
            opex_val += (
                sum(model.eps[WWTP, 'L3', t]() * (model.A[WWTP,'L3']* model.x[WWTP,'L3',t]() + model.B[WWTP,'L3']) * (1+model.int)**t for t in model.t)
                +sum(model.eps[WWTP, 'L2',t]() * (model.A[WWTP,'L2']* model.x[WWTP,'L2',t]() + model.B[WWTP,'L2']) * (1+model.int)**t for t in model.t)
                + sum(model.eps[WWTP, 'SS',t]() * (model.A[WWTP,'SS']* model.x[WWTP,'SS',t]() + model.B[WWTP,'SS']) * (1+model.int)**t for t in model.t)
                + sum(model.eps[WWTP, 'L2pt5',t]() * (model.A[WWTP,'L2pt5']* model.x[WWTP,'L2',t]() +  model.A[WWTP,'L3']* model.x[WWTP,'L2pt5',t]() + model.B[WWTP,'L2pt5']) * (1+model.int)**t for t in model.t)
            )
            opex[WWTP] = opex_val
        
        return opex

    def calculate_capex(self, model):
        """
        Calculate the capital cost of the upgrades
        Units: mil USD (not adjusted for NPV)
        """
        
        capex = {}
        for WWTP in model.WWTP:
            capex_val = (
                model.eps[WWTP,'L3',299]() * (model.D[WWTP,'L3'] * model.x_max[WWTP, 'L3']() + model.E[WWTP,'L3'])
                + model.eps[WWTP,'L2',299]() * (model.D[WWTP,'L2'] * model.x_max[WWTP, 'L2']() + model.E[WWTP,'L2'])
                + model.eps[WWTP,'SS',299]() * (model.D[WWTP,'SS'] * model.x_max[WWTP, 'SS']() + model.E[WWTP,'SS'])
                + model.eps[WWTP,'L2pt5',299]() * (model.D[WWTP,'L2pt5'] * model.x_max[WWTP,'L2']() + model.D[WWTP,'L3']* model.x_max[WWTP, 'L2pt5']() + model.E[WWTP,'L2pt5'])
            )
            capex[WWTP] = capex_val
        
        return capex


    
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
                    ax1.plot(self.datetime, [model.x[WWTP,L,t]() for t in model.t], '-', color = colors[L],label = 'Quantity removed with ' + L)

            ax1.plot(self.datetime, [model.r[WWTP,t]() for t in model.t], '-', color='orange', label = 'Total quantity removed')
            ax1.plot(self.datetime, [model.dis_minus_reg[WWTP,t] for t in model.t],  '--', color='blue', label = 'Required TIN removal', alpha=0.5)

            if self.seasonal_regulation:
                ax1.set_ylim(-500, round(max([model.dis_minus_reg[WWTP,t] for t in model.t])+100, -1))
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
        ax1.plot(self.datetime, [sum(model.dis_minus_reg[WWTP,t] for WWTP in model.WWTP) for t in model.t] , '--', color='blue', label = 'Required TIN removal', alpha=0.5)
        

        if self.seasonal_regulation:
            ax1.set_ylim(-500, round(max([sum(model.dis_minus_reg[WWTP,t] for WWTP in model.WWTP) for t in model.t])+100, -1))
            
        plt.legend()
        plt.xlabel('Year')
        plt.ylabel('TIN removed (Kg N/day)')
        plt.show()
        #fig.savefig("discharge_post.png")

        return fig, ax1


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
        