"""
=============================================================================
AI ENGINE — The "Brain" of Our Traffic Signal Controller
=============================================================================

This module uses the A* Search Algorithm to find the best traffic signal
timing. Think of it like a chess player who looks several moves ahead to
pick the best move — our AI looks several time-steps ahead to decide
whether to keep the current green signal or switch it.

Key Concepts Used:
    - A* Search Algorithm (a smart way to explore possible futures)
    - Heuristic Function (an educated guess about remaining cost)
    - State Space Search (exploring different possible signal timings)

Written for clarity so that a high school student can follow along!
=============================================================================
"""

import heapq   # Built-in Python library for priority queues (min-heaps)
import copy     # Used to make deep copies of data structures


# =============================================================================
# CONSTANTS — These control how the traffic signal AI behaves
# =============================================================================

# Signal phases (think of these as "modes" the traffic light can be in)
PHASE_NS = 0        # North-South roads have GREEN light
PHASE_EW = 1        # East-West roads have GREEN light
PHASE_YELLOW = 2    # Yellow/Amber warning — signal is about to change

# Simulation timing parameters
STEP_SIZE = 5       # Each "step" in our AI's lookahead = 5 seconds of real time
SATURATION_FLOW = 2 # Max cars that can pass through per step (per lane)

# Safety constraint — in real life, green lights can't be too short!
MIN_GREEN_TIME = 15  # Minimum seconds a green light must stay on


# =============================================================================
# SEARCH STATE — One "snapshot" of the intersection
# =============================================================================

class SearchState:
    """
    Represents one possible "state" of the intersection at a point in time.

    Imagine taking a photograph of the intersection — this class stores:
        - How many cars are waiting in each lane  (queues)
        - What color the traffic light is showing (phase)
        - How long the current phase has been on  (phase_time)
        - The total "cost" (delay) accumulated     (cost_so_far)
        - The sequence of decisions made so far     (history)

    The A* algorithm creates thousands of these states to explore different
    possible futures and find the path with the LEAST total delay.
    """

    # __slots__ tells Python to use a compact internal representation
    # instead of a dictionary for storing attributes. This saves memory
    # when we create thousands of SearchState objects during search.
    __slots__ = ['queues', 'phase', 'phase_time', 'cost_so_far', 'history', 'last_green']

    def __init__(self, queues, phase, phase_time, cost_so_far=0, history=None, last_green=PHASE_NS):
        """
        Create a new search state.

        Args:
            queues (dict):    Cars waiting per direction  {'N': 3, 'S': 2, 'E': 5, 'W': 1}
            phase (int):      Current signal phase (PHASE_NS / PHASE_EW / PHASE_YELLOW)
            phase_time (int): Seconds the current phase has been active
            cost_so_far (float): Total accumulated delay cost from the start
            history (list):   List of actions taken to reach this state
            last_green (int): The last direction that had a green light
        """
        self.queues = dict(queues)          # Copy so we don't modify the original
        self.phase = phase
        self.phase_time = phase_time
        self.cost_so_far = cost_so_far
        self.history = history if history is not None else []
        self.last_green = last_green

    def __lt__(self, other):
        """
        Comparison method used by the priority queue.

        A* always explores the state with the LOWEST estimated total cost.
        Total cost = (actual cost so far) + (heuristic estimate of remaining cost)

        This is what makes A* "smart" — it focuses on the most promising paths!
        """
        my_total = self.cost_so_far + self.get_heuristic()
        other_total = other.cost_so_far + other.get_heuristic()
        return my_total < other_total

    def get_heuristic(self):
        """
        The heuristic function — an "educated guess" about future delay.

        Formula:  (total_cars_waiting)² / (2 × cars_served_per_step)

        Why squared?  Because the more cars are waiting, the delay grows
        much faster (like a traffic jam getting worse and worse).

        IMPORTANT: This heuristic is "admissible" — it NEVER overestimates
        the true cost. This guarantees A* finds the optimal solution!

        Returns:
            float: Estimated remaining delay cost
        """
        total_waiting = sum(self.queues.values())
        return (total_waiting ** 2) / (2 * SATURATION_FLOW)

    def get_valid_actions(self):
        """
        What actions are legal from this state?

        Rules:
            1. YELLOW phase  → must go TO_GREEN  (can't stay yellow forever!)
            2. Green < 15 sec → must KEEP         (safety: drivers need reaction time)
            3. Otherwise     → KEEP or SWITCH     (the AI decides which is better)

        Returns:
            list: Valid action strings, e.g. ["KEEP", "SWITCH"]
        """
        if self.phase == PHASE_YELLOW:
            return ["TO_GREEN"]                     # Yellow → must transition

        if self.phase_time < MIN_GREEN_TIME:
            return ["KEEP"]                         # Safety: minimum green duration

        return ["KEEP", "SWITCH"]                   # AI chooses the best option

    def transition(self, action):
        """
        Simulate what happens when we take an action.

        Creates a NEW state representing the intersection after one time step.
        Think of it like pressing "fast-forward" on a simulation.
        """
        next_queues = copy.deepcopy(self.queues)
        next_history = list(self.history) + [action]
        next_last_green = self.last_green

        if self.phase == PHASE_NS:
            next_queues['N'] = max(0, next_queues['N'] - SATURATION_FLOW)
            next_queues['S'] = max(0, next_queues['S'] - SATURATION_FLOW)
        elif self.phase == PHASE_EW:
            next_queues['E'] = max(0, next_queues['E'] - SATURATION_FLOW)
            next_queues['W'] = max(0, next_queues['W'] - SATURATION_FLOW)

        if action == "SWITCH":
            next_phase = PHASE_YELLOW
            next_phase_time = STEP_SIZE
            next_last_green = self.phase  # Update last_green when we leave a green phase
        elif action == "TO_GREEN":
            next_phase = PHASE_EW if self.last_green == PHASE_NS else PHASE_NS
            next_phase_time = STEP_SIZE
        else:
            next_phase = self.phase
            next_phase_time = self.phase_time + STEP_SIZE

        step_cost = sum(next_queues.values()) * STEP_SIZE
        return SearchState(
            next_queues, next_phase, next_phase_time,
            self.cost_so_far + step_cost, next_history, next_last_green
        )


# =============================================================================
# A* SEARCH — The core algorithm that plans the optimal signal timing
# =============================================================================

def compute_astar_action(current_queues, current_phase, phase_time, last_green):
    """
    The main AI function!  Uses A* Search to find the best traffic action.

    How it works (simplified):
        1. Start from the current intersection state
        2. Look at all possible futures (keep green?  switch to yellow?)
        3. For each future, look even further ahead (up to 5 steps)
        4. Pick the action that leads to the LEAST total waiting time

    This is exactly like a chess engine thinking several moves ahead!

    Args:
        current_queues (dict): Cars waiting in each direction right now
        current_phase (int):   Current signal phase
        phase_time (int):      How long current phase has been active
        last_green (int):      Which direction had the last green signal

    Returns:
        tuple: (best_action_string, nodes_expanded_count)
            - best_action  : "KEEP", "SWITCH", or "TO_GREEN"
            - nodes_expanded: how many states the AI explored (for stats)
    """
    # Create the starting state (the "root" of our search tree)
    root = SearchState(current_queues, current_phase, phase_time, cost_so_far=0, history=None, last_green=last_green)

    # Priority queue (min-heap) — always gives us the most promising state first
    # This is what makes A* efficient: it doesn't waste time on bad paths!
    open_set = []
    heapq.heappush(open_set, root)

    best_state = None                   # Best solution found so far
    min_total_cost = float('inf')       # Start with infinity (any real cost beats this)
    nodes_expanded = 0                  # Counter for statistics

    # Keep exploring until we've checked all promising paths
    while open_set:
        # Pop the state with the LOWEST estimated total cost
        current = heapq.heappop(open_set)
        nodes_expanded += 1

        # --- Depth limit ---
        # We only look 5 steps into the future (otherwise search takes too long!)
        # When we hit the limit, evaluate this path and remember if it's the best
        if len(current.history) >= 5:
            total_cost = current.cost_so_far + current.get_heuristic()
            if total_cost < min_total_cost:
                min_total_cost = total_cost
                best_state = current
            continue    # Don't expand further

        # --- Expand: try every valid action from this state ---
        for action in current.get_valid_actions():
            neighbor = current.transition(action)
            heapq.heappush(open_set, neighbor)

    # Return the FIRST action of the best path we found.
    # (We planned 5 steps ahead but only execute step 1 now.
    #  Next call, we re-plan with fresh data — "receding horizon" planning.)
    if best_state and best_state.history:
        return (best_state.history[0], nodes_expanded)
    return ("KEEP", nodes_expanded)