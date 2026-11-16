import networkx as nx
from mesa import Model

from agent import VesselAgent
from utils import update_fuel_price, compute_enpv
from fuel_price_api import get_fuel_price_with_fallback


class WASPAdoptionModel(Model):
    """
    Agent-Based Model for WASP adoption
    """

    def __init__(
        self,
        vessel_data,
        fuel_price_start = None, 
        # Fetched from API, with backup option 500 based on Chica et al. (2023)
        fuel_price_growth = None,
        # Fetched from API, with backup option 0.005 based on Chica et al. (2023)
        use_fuel_price_api = True,
        # Enable/disable API integration
        p = 0.00118, 
        # External influence p based on Chica et al. (2023):
        # With probability p, a basic agent becomes an adopter (aware of the technology) due to outside effects (i.e., information from outside the network,
        # where p  is the external influence coefficient)
        q = 0.039, 
        # Internal influence q based on Chica et al. (2023):
        # With probability q, a basic agent becomes an adopter due to observation of the state of its neighbors.
        discount_rate = 0.085,
        wasp_capex = 500_000, 
        # Installation costs based on Chica et al. (2023) wingsail estimates
        wasp_opex_monthly = 833.33, 
        # Monthly maintenance cost based on Chica et al. (2023) wingsail estimates
        fuel_saving_ratio = 0.1385, 
        # Fuel savings based on Chica et al. (2023) wingsail estimates
        months = 360,
        seed = 1,
        initial_awareness_share = 0.01,
        reporting_active = True,
        reporting_coverage = 1.0,
        operational_noise = None,
    ):
        super().__init__(seed = seed)

        self.time = 0
        self.months = months

        # Economic parameters
        # Fetch fuel price from API if enabled and not provided
        if use_fuel_price_api and (fuel_price_start is None or fuel_price_growth is None):
            print("Fetching fuel price data from API...")
            api_price, api_growth = get_fuel_price_with_fallback(
                default_price=500.0 if fuel_price_start is None else fuel_price_start,
                default_growth=0.005 if fuel_price_growth is None else fuel_price_growth
            )
            self.fuel_price = api_price if fuel_price_start is None else fuel_price_start
            self.fuel_price_growth = api_growth if fuel_price_growth is None else fuel_price_growth
        else:
            # Use provided values or defaults
            self.fuel_price = fuel_price_start if fuel_price_start is not None else 500.0
            self.fuel_price_growth = fuel_price_growth if fuel_price_growth is not None else 0.005

        self.discount_rate = discount_rate
        self.wasp_capex = wasp_capex
        self.wasp_opex_monthly = wasp_opex_monthly
        self.fuel_saving_ratio = fuel_saving_ratio

        # Diffusion parameters
        self.p = p
        self.q = q
        self.initial_awareness_share = initial_awareness_share

        # Reporting
        self.reporting_active = reporting_active
        self.reporting_coverage = reporting_coverage
        self.operational_noise = operational_noise or 0.02 * fuel_saving_ratio
        self.reported_savings = []

        # Network and agents
        self.network = nx.barabasi_albert_graph(len(vessel_data), m = 3)

        self.vessels = []
        for node, (_, row) in zip(self.network.nodes(), vessel_data.iterrows()):
            agent = VesselAgent(
                unique_id = node,
                model = self,
                age_years = row["age"],
                fuel_use_monthly = row["fuel"],
                mileage_annual = row["miles"],
                co2_monthly_kg = row["co2_monthly_kg"],
            )
            agent.node_id = node
            self.network.nodes[node]["agent"] = agent
            self.vessels.append(agent)

        # Initial awareness
        seed_n = int(round(self.initial_awareness_share * len(self.vessels)))
        if seed_n > 0:
            for a in self.random.sample(self.vessels, seed_n):
                a.aware = True

        # Outputs
        self.adoption_history = []
        self.co2_baseline_history = []
        self.co2_saved_history = []
        self.co2_net_history = []
        self.fuel_baseline_history = []
        self.fuel_saved_history = []
        self.fuel_net_history = []

    # ENPV computation
    def compute_enpv(self, agent, saving_ratio = None):
        return compute_enpv(
            remaining_life = agent.remaining_life,
            fuel_use_monthly = agent.fuel_use_monthly,
            fuel_price = self.fuel_price,
            fuel_price_growth = self.fuel_price_growth,
            saving_ratio = saving_ratio if saving_ratio is not None else self.fuel_saving_ratio,
            capex = self.wasp_capex,
            opex_monthly = self.wasp_opex_monthly,
            discount_rate = self.discount_rate,
        )


    # Step function

    def step(self):
        if self.time >= self.months:
            return

        # Update fuel price
        self.fuel_price = update_fuel_price(self.fuel_price, self.fuel_price_growth)

        # Step all agents
        for a in self.vessels:
            a.step()

        # Track fuel and CO2
        fuel_baseline = sum(a.fuel_use_monthly for a in self.vessels)
        fuel_saved = sum(a.fuel_use_monthly * self.fuel_saving_ratio for a in self.vessels if a.adopted)
        fuel_net = fuel_baseline - fuel_saved
        
        # EU MRV-data-based CO2 approximates
        co2_baseline = sum(a.co2_monthly_kg for a in self.vessels)

        co2_saved = sum(
            a.co2_monthly_kg * self.fuel_saving_ratio
            for a in self.vessels if a.adopted
        )

        co2_net = co2_baseline - co2_saved

        self.fuel_baseline_history.append(fuel_baseline)
        self.fuel_saved_history.append(fuel_saved)
        self.fuel_net_history.append(fuel_net)
        self.co2_baseline_history.append(co2_baseline)
        self.co2_saved_history.append(co2_saved)
        self.co2_net_history.append(co2_net)

        # Adoption
        adopted = sum(a.adopted for a in self.vessels)
        self.adoption_history.append(adopted)

        self.time += 1
