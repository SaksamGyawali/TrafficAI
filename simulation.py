"""
=============================================================================
SIMULATION — The Virtual Intersection World
=============================================================================

This module creates a virtual 4-way intersection with cars that:
    - Spawn from all four directions (North, South, East, West)
    - Queue up at red lights and wait patiently
    - Drive through when the light turns green
    - Disappear after they've crossed

Think of it like a simplified version of SimCity's traffic system!

Key Concepts Used:
    - Object-Oriented Programming  (classes for vehicles and the environment)
    - 2D Coordinate System         (x, y positions for drawing on screen)
    - Physics Simulation           (movement, speed, collision avoidance)
    - Statistics Tracking          (measuring how well the AI performs)
=============================================================================
"""

import random
import time


# =============================================================================
# CONSTANTS — Dimensions of the road area
# =============================================================================

ROAD_W = 800    # Width of the road simulation area in pixels
ROAD_H = 800    # Height of the road simulation area in pixels

# A palette of colours for vehicles — each car gets a random colour!
# Every colour is an (Red, Green, Blue) tuple with values 0–255.
VEHICLE_COLORS = [
    (97, 175, 239),    # Sky Blue
    (224, 108, 117),   # Coral Red
    (229, 192, 123),   # Warm Yellow
    (152, 195, 121),   # Leaf Green
    (198, 120, 221),   # Lavender Purple
    (86, 182, 194),    # Teal Cyan
    (255, 150, 100),   # Sunset Orange
    (170, 140, 220),   # Soft Violet
]


# =============================================================================
# VEHICLE — Represents a single car on the road
# =============================================================================

class VehicleGraphic:
    """
    Represents a single car in the simulation.

    Each vehicle has:
        - A direction  ('N', 'S', 'E', or 'W')
        - A position along its path called "progress" (0.0 → 1.0)
        - A speed at which it moves forward each frame
        - A colour picked randomly from VEHICLE_COLORS
        - A flag tracking whether it has crossed the intersection line

    How "progress" works (like a percentage ruler):
        0.00  →  Car just appeared at the edge of the screen
        0.40  →  Car is approaching the stop line (intersection)
        0.42  →  Car is crossing through the intersection
        1.00  →  Car has exited the other side of the screen
    """

    def __init__(self, direction, index):
        """
        Create a new vehicle.

        Args:
            direction (str): 'N', 'S', 'E', or 'W'
            index (int):     Queue position (0 = front of queue, 1 = second, …)
        """
        self.direction = direction
        self.index = index

        # Starting position: cars further back in the queue are staggered
        # behind (negative progress means the car hasn't appeared on screen yet)
        self.progress = 0.0 - (index * 0.05)

        self.speed = 0.006          # Movement per frame (small for smooth motion)
        self.crossed_line = False   # Has this car passed through the intersection?
        self.waiting_frames = 0     # How long this car has been stopped (for stats)

        # Pick a random colour so not every car looks the same
        self.color = random.choice(VEHICLE_COLORS)

    def update(self, is_green, lead_vehicle_progress):
        """
        Move this vehicle forward by one animation frame.

        Movement rules (just like real traffic!):
            1. If there's a car right in front  → STOP  (avoid a crash!)
            2. If the light is GREEN             → DRIVE through
            3. If past the intersection already  → KEEP GOING
            4. If the light is RED               → Drive up to the stop line, then wait

        Args:
            is_green (bool):               True if this direction has a green light
            lead_vehicle_progress (float): Progress of the car directly ahead,
                                           or None if we're first in line
        """
        # The "stop line" — where this car should stop when the light is red.
        # Cars further back in the queue stop further from the intersection.
        stop_boundary = 0.40 - (self.index * 0.04)

        # --- Collision avoidance ---
        # Maintain a safe gap from the car in front (like "safe following distance")
        buffer_zone = 0.045
        blocked_by_car = (
            lead_vehicle_progress is not None
            and (lead_vehicle_progress - self.progress) < buffer_zone
        )

        if blocked_by_car:
            self.waiting_frames += 1    # Stuck behind another car
            return                      # Don't move

        # --- Decide whether to move ---
        if is_green or self.progress > 0.42:
            # Green light OR already past the intersection → drive forward!
            self.progress += self.speed
        elif self.progress < stop_boundary:
            # Red light, but haven't reached stop line yet → approach slowly
            self.progress = min(stop_boundary, self.progress + self.speed)
            if self.progress >= stop_boundary:
                self.waiting_frames += 1    # Just arrived at stop line
        else:
            # Red light and already at the stop line → wait
            self.waiting_frames += 1

    def get_coordinates(self):
        """
        Convert abstract "progress" into pixel (x, y) coordinates for drawing.

        Each direction maps progress to a different path on screen:
            S (Southbound) → starts at top,    moves down   (y increases)
            N (Northbound) → starts at bottom, moves up     (y decreases)
            E (Eastbound)  → starts at left,   moves right  (x increases)
            W (Westbound)  → starts at right,  moves left   (x decreases)

        Returns:
            tuple: (x, y) pixel coordinates on the screen
        """
        mid_w = ROAD_W // 2    # Horizontal centre of road area (400)
        mid_h = ROAD_H // 2    # Vertical centre of road area   (400)

        if self.direction == 'S':
            return (mid_w - 25, int(self.progress * ROAD_H))
        elif self.direction == 'N':
            return (mid_w + 5, int((1 - self.progress) * ROAD_H))
        elif self.direction == 'E':
            return (int(self.progress * ROAD_W), mid_h + 5)
        elif self.direction == 'W':
            return (int((1 - self.progress) * ROAD_W), mid_h - 25)


# =============================================================================
# INTERSECTION ENVIRONMENT — The "game world" that manages everything
# =============================================================================

class IntersectionEnvironment:
    """
    The main simulation world.

    Responsibilities:
        - Track how many cars are waiting in each direction  (queues)
        - Spawn new cars  (manually via keyboard, or randomly)
        - Update all car positions each frame  (physics)
        - Track performance statistics  (throughput, wait times)
    """

    def __init__(self):
        """Initialise the intersection with some starting traffic."""
        # Queue counters — the AI reads these to make decisions
        self.queues = {'N': 0, 'S': 0, 'E': 0, 'W': 0}

        # Master list of all vehicle objects currently on screen
        self.vehicles = []

        # Probability that a new car spawns in a given lane each cycle
        self.spawn_rate = 0.08      # 8 % chance per lane per cycle

        # ---- Statistics ----
        self.total_served = 0           # Total cars that crossed the intersection
        self.total_wait_frames = 0      # Sum of waiting frames (for avg calc)
        self.start_time = time.time()   # When the simulation started

        # Create some initial traffic so the intersection isn't empty
        for lane in ['N', 'S', 'E', 'W']:
            for _ in range(3):
                self.force_spawn(lane)

    # -----------------------------------------------------------------
    # Spawning vehicles
    # -----------------------------------------------------------------

    def force_spawn(self, lane):
        """
        Manually add a new car to the given lane.

        Called when the user presses N / S / E / W keys, and also during
        initialisation to create starting traffic.

        Args:
            lane (str): 'N', 'S', 'E', or 'W'
        """
        # Count existing cars in this lane that haven't crossed yet
        current_lane_count = sum(
            1 for v in self.vehicles
            if v.direction == lane and not v.crossed_line
        )
        # Create the vehicle and add it to the world
        self.vehicles.append(VehicleGraphic(lane, current_lane_count))
        self.queues[lane] += 1

    def process_ambient_flow(self):
        """
        Simulate random background traffic arriving at the intersection.

        In real life cars arrive somewhat randomly — this function gives each
        lane a small random chance of getting a new car each cycle.
        """
        for lane in ['N', 'S', 'E', 'W']:
            if random.random() < self.spawn_rate:
                self.force_spawn(lane)

    # -----------------------------------------------------------------
    # Physics & queue updates
    # -----------------------------------------------------------------

    def step_queues(self, phase, flow_rate):
        """
        Adjust queue counters based on which direction has green.
        Used by the AI engine for internal bookkeeping.

        Args:
            phase (int):     Current signal phase (0 = NS, 1 = EW)
            flow_rate (float): Cars that can pass per step
        """
        if phase == 0:
            self.queues['N'] = max(0, self.queues['N'] - flow_rate)
            self.queues['S'] = max(0, self.queues['S'] - flow_rate)
        elif phase == 1:
            self.queues['E'] = max(0, self.queues['E'] - flow_rate)
            self.queues['W'] = max(0, self.queues['W'] - flow_rate)

    def update_physics(self, active_phase):
        """
        Move ALL vehicles forward by one frame and handle intersection crossings.

        This is the "physics engine" of the simulation — called every single
        frame (60 times per second) to produce smooth animation.

        Args:
            active_phase (int): Current signal phase (0 = NS green, 1 = EW green)
        """
        # Process each lane independently
        for lane in ['N', 'S', 'E', 'W']:
            # Gather cars in this lane, sorted front-most first
            lane_cars = sorted(
                [v for v in self.vehicles if v.direction == lane],
                key=lambda v: v.progress,
                reverse=True
            )

            # Does this lane currently have a green light?
            is_green = (
                (active_phase == 0 and lane in ['N', 'S']) or
                (active_phase == 1 and lane in ['E', 'W'])
            )

            for i, vehicle in enumerate(lane_cars):
                # Find the progress of the car ahead (for collision avoidance)
                lead_progress = lane_cars[i - 1].progress if i > 0 else None
                vehicle.update(is_green, lead_progress)

                # --- Check if this car just crossed the intersection ---
                if vehicle.progress >= 0.42 and not vehicle.crossed_line:
                    vehicle.crossed_line = True

                    # Record stats
                    self.total_served += 1
                    self.total_wait_frames += vehicle.waiting_frames

                    # One fewer car waiting in the queue
                    self.queues[lane] = max(0, self.queues[lane] - 1)

                    # Shift trailing cars forward in the queue
                    for trailing in lane_cars[i + 1:]:
                        trailing.index = max(0, trailing.index - 1)

        # Remove vehicles that have driven off the screen edge
        self.vehicles = [v for v in self.vehicles if v.progress < 1.0]

    # -----------------------------------------------------------------
    # Statistics helpers
    # -----------------------------------------------------------------

    def get_avg_wait_seconds(self):
        """
        Average time a car spends waiting (in seconds).

        We convert frame-count to seconds by dividing by 60
        (since the simulation runs at 60 frames per second).

        Returns:
            float: Average wait in seconds, or 0.0 if no cars served yet
        """
        if self.total_served == 0:
            return 0.0
        return (self.total_wait_frames / self.total_served) / 60.0

    def get_throughput_per_minute(self):
        """
        How many cars cross the intersection per minute.

        Returns:
            float: Vehicles per minute
        """
        elapsed = time.time() - self.start_time
        if elapsed < 1:
            return 0.0
        return (self.total_served / elapsed) * 60.0