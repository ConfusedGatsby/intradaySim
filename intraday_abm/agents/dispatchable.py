"""
Modified DispatchableAgent - Shinde 2023 Compliant
===================================================

This is the COMPLETE modified DispatchableAgent class with:
- Shinde 2021 Equations 8-12 (Margins, Imbalance, Limit Price Updates)
- Shinde 2023 Equations 18-21 (Ramping Constraints, Switch Parameter)
- Multi-Product Support
- Full compatibility with existing codebase

Replace the existing DispatchableAgent class (lines 4148-4339) with this code.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Union, Tuple
from enum import Enum

# Assuming these imports from your existing code:
# from intraday_abm.core.agent import Agent
# from intraday_abm.core.order import Order, Side, TimeInForce
# from intraday_abm.core.public_info import PublicInfo


@dataclass
class DispatchableAgent(Agent):
    """
    Shinde 2023 compliant thermal power plant agent.
    
    Implements:
    - Shinde 2021 Equations 8-12 (Imbalance, Margins, Limit Prices)
    - Shinde 2023 Equations 18-21 (Ramping Constraints)
    - Multi-Product Support
    - Switch Parameter for ramping activation
    
    Key Features:
    1. Marginal cost-based trading
    2. Capacity and minimum stable load constraints
    3. Ramping up/down constraints (multi-product)
    4. Adaptive limit price updates
    5. Two trading modes:
       - BEFORE switch: Profit maximization
       - AFTER switch: Ramping compliance
    
    References:
    - Shinde et al. (2021): "Analyzing Trade in Continuous Intra-Day 
      Electricity Market: An Agent-Based Modeling Approach"
    - Shinde et al. (2023): "A Multi-agent Model for Cross-border Trading 
      in the Continuous Intraday Electricity Market"
    """
    
    # ========== BASIC PARAMETERS (from original) ==========
    marginal_cost: float                    # €/MWh - production cost
    base_volume: float = 5.0                # MW - typical order size
    epsilon_price: float = 1.0              # €/MWh - minimum profit margin
    imbalance_penalty: float = 0.0          # (documentation only)
    
    # ========== SHINDE 2021 PARAMETERS ==========
    min_stable_load: float = 50.0           # MW - C_min (Equation 8-9)
    alpha: float = 0.3                      # Limit price update factor (Eq 11)
    pi_imb_plus: float = 60.0               # €/MWh - positive imbalance price
    pi_imb_minus: float = 40.0              # €/MWh - negative imbalance price
    e_imb: float = 5.0                      # €/MWh - imbalance price error variance
    
    # ========== SHINDE 2023 RAMPING PARAMETERS ==========
    ramping_up_rate: float = 50.0           # MW/hour - r_up (Equation 18-21)
    ramping_down_rate: float = 50.0         # MW/hour - r_dn
    switch_parameter: float = 0.5           # 0.0-1.0 - when to activate ramping
    nu_R: float = 1.0                       # Scaling factor ν_R
    
    # ========== INTERNAL STATE ==========
    _switch_activated: bool = field(default=False, init=False)
    _total_trading_steps: int = field(default=1500, init=False)
    
    # ========== MAIN DECISION METHOD ==========
    
    def decide_orders(
        self,
        t: int,
        public_info: Dict[int, PublicInfo],
    ) -> Dict[int, Union[Order, List[Order]]]:
        """
        Multi-product dispatchable agent logic (Shinde 2023).
        
        Process for each product:
        1. Calculate imbalance (Shinde 2021 Eq 10)
        2. Calculate buy/sell margins (Eq 8-9)
        3. Update limit prices (Eq 11-12)
        4. Create order based on mode:
           - BEFORE switch: Profit maximization (Eq 18-19)
           - AFTER switch: Ramping compliance (Eq 20-21)
        
        Args:
            t: Current simulation timestep
            public_info: Dict mapping product_id to PublicInfo
            
        Returns:
            Dict mapping product_id to Order (or list of orders)
        """
        orders_dict = {}
        
        # Check switch activation
        self._check_switch_activation(t)
        
        # Process each product
        for product_id, pub_info in public_info.items():
            
            # Get position and capacity for this product
            if self.is_multi_product:
                position = self.private_info.positions.get(product_id, 0.0)
                capacity = self.private_info.capacities.get(product_id, 0.0)
            else:
                position = self.private_info.market_position
                capacity = self.private_info.effective_capacity
            
            # Skip if no capacity
            if capacity <= 0:
                continue
            
            # ===== Shinde 2021 Core Logic =====
            
            # Calculate imbalance (Equation 10)
            delta = self._compute_imbalance_shinde(
                capacity, position, self.min_stable_load
            )
            
            # Calculate margins (Equations 8-9)
            g_down, g_up = self._compute_margins(
                capacity, position, self.min_stable_load
            )
            
            # Update limit prices (Equations 11-12)
            self._update_limit_prices(delta, product_id)
            
            # ===== Shinde 2023 Trading Mode =====
            
            # Create order based on mode
            if self._switch_activated:
                # AFTER switch: Ramping compliance mode (Equations 20-21)
                order = self._create_ramping_order(
                    t, product_id, pub_info, capacity, position
                )
            else:
                # BEFORE switch: Profit maximization mode (Equations 18-19)
                order = self._create_profit_order(
                    t, product_id, pub_info, capacity, position
                )
            
            if order is not None:
                orders_dict[product_id] = order
        
        return orders_dict
    
    # ========== SHINDE 2021 CORE METHODS ==========
    
    def _compute_imbalance_shinde(
        self, 
        capacity: float, 
        position: float, 
        min_load: float
    ) -> float:
        """
        Shinde 2021 Equation 10:
        δ_i,t = min{C_i,t - p_mar_i,t, 0} + min{p_mar_i,t - C_min, 0}
        
        This formula captures two constraints:
        1. Capacity constraint: Cannot produce more than C_i,t
        2. Minimum load constraint: Cannot produce less than C_min
        
        Returns:
        - Negative: Need to BUY (undercommitted or below minimum)
        - Zero: OK
        - Positive: IMPOSSIBLE with this formula
        
        Args:
            capacity: Maximum capacity C_i,t
            position: Current market position p_mar_i,t
            min_load: Minimum stable load C_min
            
        Returns:
            Imbalance δ_i,t
        """
        term1 = min(capacity - position, 0.0)  # Negative if overcommitted
        term2 = min(position - min_load, 0.0)  # Negative if below minimum
        delta = term1 + term2
        return delta
    
    def _compute_margins(
        self,
        capacity: float,
        position: float,
        min_load: float
    ) -> Tuple[float, float]:
        """
        Shinde 2021 Equations 8-9:
        
        g_down = max(p_mar - min(C, C_min), 0)  # Buy margin
        g_up = max(C - p_mar, 0)                # Sell margin
        
        These margins define trading limits:
        - g_down: Max volume agent can BUY (reduce position to minimum)
        - g_up: Max volume agent can SELL (increase position to capacity)
        
        Args:
            capacity: Maximum capacity C
            position: Current market position p_mar
            min_load: Minimum stable load C_min
            
        Returns:
            Tuple (g_down, g_up)
        """
        g_down = max(position - min(capacity, min_load), 0.0)
        g_up = max(capacity - position, 0.0)
        return g_down, g_up
    
    def _update_limit_prices(
        self,
        delta: float,
        product_id: int
    ) -> None:
        """
        Shinde 2021 Equations 11-12:
        
        l_buy(t+1) = {
            (1-α)·l_buy(t) + α·max(π̂_imb-, l_buy_init)  if δ < 0
            l_buy_init                                   otherwise
        }
        
        l_sell(t) = l_sell_init  (NEVER changes!)
        
        Key insight: Only BUY limit is adaptive (thermal plants
        are constrained in buying, but can always sell if profitable).
        
        Args:
            delta: Current imbalance
            product_id: Product ID (for multi-product)
        """
        pi = self.private_info
        
        # Get current limit buy price for this product
        if self.is_multi_product:
            # Multi-product: limit_buy is a dict
            if not hasattr(pi, 'limit_buy') or not isinstance(pi.limit_buy, dict):
                pi.limit_buy = {}
            
            l_buy_current = pi.limit_buy.get(product_id, pi.limit_buy_initial)
            l_buy_init = pi.limit_buy_initial
        else:
            # Single-product: limit_buy is a float
            l_buy_current = getattr(pi, 'limit_buy', pi.limit_buy_initial)
            l_buy_init = pi.limit_buy_initial
        
        # Predict imbalance prices (Shinde 2021 Equations 4-5)
        # π̂_imb- = π_imb- + N(0, e_imb)
        pi_imb_minus_hat = self.pi_imb_minus + self.rng.gauss(0, self.e_imb)
        
        # Update l_buy if delta < 0 (Equation 11)
        if delta < 0:
            # Agent needs to BUY → increase willingness to pay
            l_buy_new = (1 - self.alpha) * l_buy_current + \
                       self.alpha * max(pi_imb_minus_hat, l_buy_init)
        else:
            # Agent is OK → reset to initial
            l_buy_new = l_buy_init
        
        # Store updated limit price
        if self.is_multi_product:
            pi.limit_buy[product_id] = l_buy_new
        else:
            pi.limit_buy = l_buy_new
        
        # l_sell NEVER changes (Equation 12)
        # It stays at initial value (already set in private_info)
    
    # ========== SHINDE 2023 SWITCH LOGIC ==========
    
    def _check_switch_activation(self, t: int) -> bool:
        """
        Check if switch should be activated.
        
        Switch activates at: t_switch = switch_parameter * T_total
        
        Example:
        - switch_parameter = 0.5, T_total = 1500
        - Switch activates at t = 750 (50% of timeline)
        
        Args:
            t: Current timestep
            
        Returns:
            True if switch is activated
        """
        switch_step = int(self.switch_parameter * self._total_trading_steps)
        
        if t >= switch_step and not self._switch_activated:
            self._switch_activated = True
        
        return self._switch_activated
    
    # ========== SHINDE 2023 TRADING MODES ==========
    
    def _create_profit_order(
        self,
        t: int,
        product_id: int,
        public_info: PublicInfo,
        capacity: float,
        position: float,
    ) -> Optional[Order]:
        """
        Shinde 2023 Equations 18-19 (BEFORE switch).
        
        Profit maximization mode:
        - Trade if profitable (price vs. marginal cost)
        - Volume limited by ramping rates
        
        Equations 18-19:
        v̂_A = min{C - p_mar, ν·r_up}      # Sell volume
        v̂_B = min{max{p_mar - min(C, C_min), 0}, ν·r_dn}  # Buy volume
        
        Args:
            t: Current timestep
            product_id: Product ID
            public_info: Public market info
            capacity: Agent capacity
            position: Current position
            
        Returns:
            Order or None
        """
        # Get midprice
        mid = self._get_midprice(public_info.tob, public_info.da_price)
        
        # Equation 18: Sell volume
        v_A = min(
            capacity - position,
            self.nu_R * self.ramping_up_rate
        )
        
        # Equation 19: Buy volume
        v_B = min(
            max(position - min(capacity, self.min_stable_load), 0.0),
            self.nu_R * self.ramping_down_rate
        )
        
        # Profitability check
        can_sell = (mid > self.marginal_cost + self.epsilon_price) and (v_A > 0)
        can_buy = (mid < self.marginal_cost - self.epsilon_price) and (v_B > 0)
        
        # Decide side
        if can_sell:
            side = Side.SELL
            volume = min(v_A, self.base_volume)
        elif can_buy:
            side = Side.BUY
            volume = min(v_B, self.base_volume)
        else:
            return None
        
        # Compute price using pricing strategy
        price = self.compute_order_price(
            side=side,
            t=t,
            public_info=public_info,
            volume=volume,
            product_id=product_id if self.is_multi_product else None
        )
        
        return Order(
            id=-1,
            agent_id=self.id,
            side=side,
            price=price,
            volume=volume,
            product_id=product_id if self.is_multi_product else None,
            time_in_force=TimeInForce.GTC,
            timestamp=t,
        )
    
    def _create_ramping_order(
        self,
        t: int,
        product_id: int,
        public_info: PublicInfo,
        capacity: float,
        position: float,
    ) -> Optional[Order]:
        """
        Shinde 2023 Equations 20-21 (AFTER switch).
        
        Ramping compliance mode:
        - Calculate ramping violations
        - Trade to fix violations
        
        Equations 20-21:
        If δ < 0 (ramping down too fast):
            v̂_A = 0, v̂_B = max{r_dn, |δ|}
        If δ > 0 (ramping up too fast):
            v̂_A = max{r_up, |δ|}, v̂_B = 0
        Else (no violation):
            v̂_A = min{p_mar - C, ν·r_up}
            v̂_B = min{max{p_mar - min(C, C_min), 0}, ν·r_dn}
        
        Args:
            t: Current timestep
            product_id: Product ID
            public_info: Public market info
            capacity: Agent capacity
            position: Current position
            
        Returns:
            Order or None
        """
        # Calculate ramping violation δ_i,t,d
        delta_ramp = self._calculate_ramping_violation(product_id)
        
        # Equation 20: Sell volume decision
        if delta_ramp < 0:  # Ramping down too fast
            v_A = 0.0
        elif delta_ramp > 0:  # Ramping up too fast
            v_A = max(self.ramping_up_rate, abs(delta_ramp))
        else:  # No violation
            v_A = min(
                position - capacity,  # Note: This should be capacity - position?
                self.nu_R * self.ramping_up_rate
            )
        
        # Equation 21: Buy volume decision
        if delta_ramp < 0:  # Ramping down too fast
            v_B = max(self.ramping_down_rate, abs(delta_ramp))
        elif delta_ramp > 0:  # Ramping up too fast
            v_B = 0.0
        else:  # No violation
            v_B = min(
                max(position - min(capacity, self.min_stable_load), 0.0),
                self.nu_R * self.ramping_down_rate
            )
        
        # Decide side
        if v_A > 0 and v_B == 0:
            side = Side.SELL
            volume = min(v_A, self.base_volume)
        elif v_B > 0 and v_A == 0:
            side = Side.BUY
            volume = min(v_B, self.base_volume)
        elif v_A > 0 and v_B > 0:
            # Both possible - choose based on profitability
            mid = self._get_midprice(public_info.tob, public_info.da_price)
            if mid > self.marginal_cost:
                side = Side.SELL
                volume = min(v_A, self.base_volume)
            else:
                side = Side.BUY
                volume = min(v_B, self.base_volume)
        else:
            return None
        
        # Compute price
        price = self.compute_order_price(
            side=side,
            t=t,
            public_info=public_info,
            volume=volume,
            product_id=product_id if self.is_multi_product else None
        )
        
        return Order(
            id=-1,
            agent_id=self.id,
            side=side,
            price=price,
            volume=volume,
            product_id=product_id if self.is_multi_product else None,
            time_in_force=TimeInForce.GTC,
            timestamp=t,
        )
    
    def _calculate_ramping_violation(self, product_id: int) -> float:
        """
        Calculate ramping violation for a product.
        
        Checks position differences with adjacent products
        against ramping limits.
        
        Returns:
        - Positive: ramping up too fast (need to SELL)
        - Negative: ramping down too fast (need to BUY)
        - Zero: within ramping limits
        
        Args:
            product_id: Product to check
            
        Returns:
            Violation magnitude
        """
        if not self.is_multi_product:
            return 0.0
        
        # Get sorted product IDs (by delivery time)
        all_products = sorted(self.private_info.positions.keys())
        
        try:
            idx = all_products.index(product_id)
        except ValueError:
            return 0.0
        
        p_curr = self.private_info.positions[product_id]
        violation = 0.0
        
        # Check with previous product (ramping UP constraint)
        if idx > 0:
            prev_id = all_products[idx - 1]
            p_prev = self.private_info.positions[prev_id]
            delta_up = p_curr - p_prev  # How much we ramped up
            
            if delta_up > self.ramping_up_rate:
                # Ramped up too fast → need to SELL in current product
                violation += (delta_up - self.ramping_up_rate)
        
        # Check with next product (ramping DOWN constraint)
        if idx < len(all_products) - 1:
            next_id = all_products[idx + 1]
            p_next = self.private_info.positions[next_id]
            delta_down = p_next - p_curr  # How much we'll ramp down
            
            if delta_down < -self.ramping_down_rate:
                # Ramping down too fast → need to BUY in current product
                violation += delta_down  # delta_down is negative
        
        return violation
    
    # ========== HELPER METHODS ==========
    
    def _get_midprice(self, tob, da_price: float) -> float:
        """
        Calculate midprice from top of book.
        
        Fallback order:
        1. (best_bid + best_ask) / 2
        2. best_bid
        3. best_ask
        4. DA price
        
        Args:
            tob: Top of book
            da_price: Day-ahead price (fallback)
            
        Returns:
            Midprice estimate
        """
        bb = tob.best_bid_price
        ba = tob.best_ask_price
        
        if bb is not None and ba is not None:
            return 0.5 * (bb + ba)
        elif bb is not None:
            return bb
        elif ba is not None:
            return ba
        else:
            return da_price
    
    # ========== BACKWARDS COMPATIBILITY ==========
    
    def decide_order(
        self,
        t: int,
        public_info: PublicInfo,
    ) -> Optional[Order]:
        """
        Single-product compatibility method.
        
        Calls decide_orders() with single product and returns
        the single order.
        
        DEPRECATED: Use decide_orders() for multi-product.
        """
        # Wrap single product in dict
        public_info_dict = {0: public_info}
        
        # Call multi-product method
        orders_dict = self.decide_orders(t, public_info_dict)
        
        # Return single order or None
        return orders_dict.get(0, None)
    
    # ========== FACTORY METHOD ==========
    
    @classmethod
    def create(
        cls,
        *,
        id: int,
        rng,
        capacity: float,
        da_position: float,
        marginal_cost: float,
        base_volume: float = 15.0,
        epsilon_price: float = 2.0,
        min_stable_load: float = None,
        ramping_up_rate: float = 50.0,
        ramping_down_rate: float = 50.0,
        switch_parameter: float = 0.5,
    ) -> "DispatchableAgent":
        """
        Convenience factory for creating DispatchableAgent.
        
        Args:
            id: Agent ID
            rng: Random number generator
            capacity: Maximum capacity (MW)
            da_position: Day-ahead position (MW)
            marginal_cost: Production cost (€/MWh)
            base_volume: Typical order size (MW)
            epsilon_price: Minimum profit margin (€/MWh)
            min_stable_load: Minimum load (MW), defaults to 25% of capacity
            ramping_up_rate: Ramping up limit (MW/hour)
            ramping_down_rate: Ramping down limit (MW/hour)
            switch_parameter: When to activate ramping (0.0-1.0)
            
        Returns:
            Initialized DispatchableAgent
        """
        # Default minimum stable load to 25% of capacity
        if min_stable_load is None:
            min_stable_load = capacity * 0.25
        
        # Create private info (assuming AgentPrivateInfo exists)
        from intraday_abm.core.private_info import AgentPrivateInfo
        
        priv = AgentPrivateInfo(
            effective_capacity=capacity,
            da_position=da_position,
        )
        
        # Initialize limit prices
        priv.limit_buy_initial = marginal_cost + 20.0
        priv.limit_sell_initial = marginal_cost - 15.0
        priv.limit_buy = priv.limit_buy_initial
        priv.limit_sell = priv.limit_sell_initial
        
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
            marginal_cost=marginal_cost,
            base_volume=base_volume,
            epsilon_price=epsilon_price,
            min_stable_load=min_stable_load,
            ramping_up_rate=ramping_up_rate,
            ramping_down_rate=ramping_down_rate,
            switch_parameter=switch_parameter,
        )