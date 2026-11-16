from mesa.agent import Agent

class VesselAgent(Agent):
    def __init__(self, unique_id, model, age_years, fuel_use_monthly, mileage_annual, co2_monthly_kg):
        super().__init__(model)
        self.node_id = None

        # Static / initial attributes
        self.age_years = age_years
        self.max_lifetime_months = 30 * 12
        self.remaining_life = self.max_lifetime_months - int(age_years * 12)

        self.fuel_use_monthly = fuel_use_monthly
        self.mileage_annual = mileage_annual
        self.co2_monthly_kg = co2_monthly_kg

        # Dynamic states
        self.aware = False
        self.adopted = False

        # Bayesian beliefs about fuel savings
        self.saving_mean = model.fuel_saving_ratio
        self.saving_std = 0.1 * model.fuel_saving_ratio
        self.risk_aversion = 1.0

        # Decision trace (for visualisation)
        self.last_expected_saving = None
        self.last_enpv = None
        self.last_posterior_mean = None
        self.last_posterior_std = None

    def step(self):
        if self.remaining_life <= 0 or self.adopted:
            return

        self.remaining_life -= 1

        if not self.aware:
            self.awareness()
        else:
            self.update_belief_from_reports()
            self.utility_decision()


    # Bass diffusion awareness

    def awareness(self):
        neighbors = list(self.model.network.neighbors(self.node_id))
        if neighbors:
            aware_neighbors = sum(
                self.model.network.nodes[n]["agent"].aware
                for n in neighbors
            )
            f = aware_neighbors / len(neighbors)
        else:
            f = 0.0

        if self.random.random() < (self.model.p + self.model.q * f):
            self.aware = True


    # Bayesian update from reports

    def update_belief_from_reports(self):
        if not self.model.reporting_active:
            return

        reports = self.model.reported_savings
        n = len(reports)
        if n == 0:
            return

        # Normal prior / normal likelihood Bayesian update
        prior_var = self.saving_std ** 2
        obs_var = self.model.operational_noise ** 2
        post_var = 1 / (1/prior_var + n/obs_var)
        post_mean = post_var * (self.saving_mean/prior_var + sum(reports)/obs_var)

        self.last_posterior_mean = post_mean
        self.last_posterior_std = post_var ** 0.5


        self.saving_mean = post_mean
        self.saving_std = post_var ** 0.5


    # Risk-adjusted utility adoption

    def utility_decision(self):
        expected_saving = self.saving_mean - self.risk_aversion * self.saving_std

        enpv = self.model.compute_enpv(self, saving_ratio = expected_saving)

        self.last_expected_saving = expected_saving
        self.last_enpv = enpv

        if enpv > 0:
            self.adopted = True

            if self.model.reporting_active:
                if self.random.random() < self.model.reporting_coverage:
                    realized_saving = (
                        self.model.fuel_saving_ratio
                        + self.random.normalvariate(0, self.model.operational_noise)
                    )
                    self.model.reported_savings.append(realized_saving)
