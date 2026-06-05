"""
=============================================================================
MAIN — The Entry Point and Visual Renderer
=============================================================================

This is the main file that ties everything together:
    1. Creates the game window using Pygame
    2. Handles keyboard input from the user
    3. Runs the A* AI engine to control traffic signals
    4. Renders the beautiful visual display
    5. Shows real-time statistics in a dashboard panel

To run:   python main.py

Controls:
    N / S / E / W   →  Spawn a car in that direction
    P               →  Pause / Resume the simulation
    H               →  Toggle the help overlay
    + / =           →  Speed up  (1× → 2× → 4×)
    - / _           →  Slow down (4× → 2× → 1×)
    Q / ESC         →  Quit

=============================================================================
"""

import pygame
import sys
import ai_engine as ai
from simulation import IntersectionEnvironment, ROAD_W, ROAD_H


# =============================================================================
# WINDOW DIMENSIONS
# =============================================================================
# The window is wider than the road area to fit a stats panel on the right.

PANEL_W = 320                       # Width of the dashboard panel (pixels)
SCREEN_W = ROAD_W + PANEL_W        # Total window width  = 800 + 320 = 1120
SCREEN_H = ROAD_H                  # Total window height = 800


# =============================================================================
# COLOUR PALETTE — A carefully chosen "One Dark" inspired colour scheme
# =============================================================================
# Every colour is an (R, G, B) tuple where R/G/B range from 0 to 255.
# 0 = no light (dark), 255 = full brightness.

# ---- Backgrounds ----
BG_COLOR = (30, 33, 40)                # Main window background (dark charcoal)
ROAD_COLOR = (55, 60, 72)              # Road surface
INTERSECTION_COLOR = (48, 53, 65)      # Intersection centre (slightly lighter)

# ---- Road markings ----
LANE_DASH_COLOR = (120, 130, 150)      # Dashed lane divider lines
SHOULDER_COLOR = (180, 180, 190)       # Solid edge-of-road lines
CROSSWALK_COLOR = (200, 200, 210)      # Pedestrian crossing stripes

# ---- Side panel ----
PANEL_BG = (22, 25, 32)               # Panel background
PANEL_BORDER = (50, 55, 68)           # Borders and dividers inside the panel

# ---- Text ----
TEXT_PRIMARY = (200, 205, 215)         # Main text (off-white)
TEXT_SECONDARY = (110, 120, 138)       # Subdued / label text
TEXT_ACCENT = (229, 192, 123)          # Highlighted text (warm yellow)
ACCENT_GREEN = (80, 220, 120)         # Titles / success colour
ACCENT_BLUE = (97, 175, 239)          # Info values

# ---- Traffic light colours (bright ON / dim OFF versions) ----
LIGHT_RED_ON = (255, 70, 70)
LIGHT_RED_OFF = (80, 25, 25)
LIGHT_YELLOW_ON = (255, 210, 60)
LIGHT_YELLOW_OFF = (80, 68, 20)
LIGHT_GREEN_ON = (60, 255, 100)
LIGHT_GREEN_OFF = (20, 80, 35)
LIGHT_HOUSING = (25, 25, 30)          # The dark box that holds the lights

# ---- Per-direction bar-chart colours ----
QUEUE_COLORS = {
    'N': (97, 175, 239),        # Blue
    'S': (152, 195, 121),       # Green
    'E': (229, 192, 123),       # Yellow
    'W': (198, 120, 221),       # Purple
}

# Speed multiplier options (cycle through with +/- keys)
SPEED_OPTIONS = [1, 2, 4]


# =============================================================================
# RENDERING HELPER FUNCTIONS
# =============================================================================
# Each function draws one "layer" of the scene.  The main loop calls them
# in order: background → roads → lights → vehicles → panel → overlays.


def draw_grid_background(screen):
    """
    Draw a subtle dotted grid on the non-road area.
    This gives the background a polished, technical appearance.
    """
    for x in range(0, ROAD_W, 40):
        for y in range(0, ROAD_H, 40):
            pygame.draw.circle(screen, (38, 42, 50), (x, y), 1)


def draw_roads(screen):
    """
    Draw the road network: surfaces, dashed lane-dividers, crosswalks,
    and solid shoulder lines.

    The intersection sits at the centre of the 800 × 800 road area.
    Each road is 120 px wide (two 60 px lanes).
    """
    mid_x = ROAD_W // 2        # Centre of road area horizontally  (400)
    mid_y = ROAD_H // 2        # Centre of road area vertically    (400)
    road_half = 60              # Half the total road width

    # ── Road surfaces ──────────────────────────────────────────────
    # North–South road (vertical strip)
    pygame.draw.rect(screen, ROAD_COLOR,
                     (mid_x - road_half, 0, road_half * 2, ROAD_H))
    # East–West road (horizontal strip)
    pygame.draw.rect(screen, ROAD_COLOR,
                     (0, mid_y - road_half, ROAD_W, road_half * 2))
    # Intersection centre (slightly different shade so it stands out)
    pygame.draw.rect(screen, INTERSECTION_COLOR,
                     (mid_x - road_half, mid_y - road_half,
                      road_half * 2, road_half * 2))

    # ── Dashed centre-lane dividers ────────────────────────────────
    # These show drivers where the lane boundaries are (just like real roads)
    dash_len = 15
    gap_len = 15

    # Vertical dashes on the N–S road
    for y in range(0, ROAD_H, dash_len + gap_len):
        if mid_y - road_half - 5 < y < mid_y + road_half + 5:
            continue                    # Skip the intersection zone
        pygame.draw.line(screen, LANE_DASH_COLOR,
                         (mid_x, y), (mid_x, min(y + dash_len, ROAD_H)), 2)

    # Horizontal dashes on the E–W road
    for x in range(0, ROAD_W, dash_len + gap_len):
        if mid_x - road_half - 5 < x < mid_x + road_half + 5:
            continue
        pygame.draw.line(screen, LANE_DASH_COLOR,
                         (x, mid_y), (min(x + dash_len, ROAD_W), mid_y), 2)

    # ── Crosswalk stripes ──────────────────────────────────────────
    # White bars painted across the road at each edge of the intersection
    stripe_w = 18
    stripe_gap = 6
    stripe_h = 4

    # Crosswalks on the vertical road (North and South edges)
    for i in range(5):
        offset = mid_x - road_half + 4 + i * (stripe_w + stripe_gap)
        # North edge
        pygame.draw.rect(screen, CROSSWALK_COLOR,
                         (offset, mid_y - road_half - stripe_h - 2,
                          stripe_w, stripe_h))
        # South edge
        pygame.draw.rect(screen, CROSSWALK_COLOR,
                         (offset, mid_y + road_half + 2,
                          stripe_w, stripe_h))

    # Crosswalks on the horizontal road (West and East edges)
    for i in range(5):
        offset = mid_y - road_half + 4 + i * (stripe_w + stripe_gap)
        # West edge
        pygame.draw.rect(screen, CROSSWALK_COLOR,
                         (mid_x - road_half - stripe_h - 2, offset,
                          stripe_h, stripe_w))
        # East edge
        pygame.draw.rect(screen, CROSSWALK_COLOR,
                         (mid_x + road_half + 2, offset,
                          stripe_h, stripe_w))

    # ── Solid shoulder (edge) lines ────────────────────────────────
    # These mark the boundaries of the road surface.
    # Vertical road — left edge
    pygame.draw.line(screen, SHOULDER_COLOR,
                     (mid_x - road_half, 0),
                     (mid_x - road_half, mid_y - road_half), 2)
    pygame.draw.line(screen, SHOULDER_COLOR,
                     (mid_x - road_half, mid_y + road_half),
                     (mid_x - road_half, ROAD_H), 2)
    # Vertical road — right edge
    pygame.draw.line(screen, SHOULDER_COLOR,
                     (mid_x + road_half, 0),
                     (mid_x + road_half, mid_y - road_half), 2)
    pygame.draw.line(screen, SHOULDER_COLOR,
                     (mid_x + road_half, mid_y + road_half),
                     (mid_x + road_half, ROAD_H), 2)
    # Horizontal road — top edge
    pygame.draw.line(screen, SHOULDER_COLOR,
                     (0, mid_y - road_half),
                     (mid_x - road_half, mid_y - road_half), 2)
    pygame.draw.line(screen, SHOULDER_COLOR,
                     (mid_x + road_half, mid_y - road_half),
                     (ROAD_W, mid_y - road_half), 2)
    # Horizontal road — bottom edge
    pygame.draw.line(screen, SHOULDER_COLOR,
                     (0, mid_y + road_half),
                     (mid_x - road_half, mid_y + road_half), 2)
    pygame.draw.line(screen, SHOULDER_COLOR,
                     (mid_x + road_half, mid_y + road_half),
                     (ROAD_W, mid_y + road_half), 2)


def draw_traffic_light(screen, x, y, active):
    """
    Draw a realistic three-circle traffic signal housing.

    Only the currently active light glows brightly; the other two are dim.
    The active light also gets a semi-transparent "glow halo" around it.

    Args:
        screen:     Pygame display surface
        x (int):    Centre-x of the traffic light
        y (int):    Centre-y of the traffic light
        active (str): Which light is on — "red", "yellow", or "green"
    """
    # The dark housing (the box around the three lights)
    housing = pygame.Rect(x - 14, y - 42, 28, 84)
    pygame.draw.rect(screen, LIGHT_HOUSING, housing, border_radius=8)
    pygame.draw.rect(screen, (60, 60, 70), housing, 2, border_radius=8)

    # Three lights stacked vertically:  (name, on_colour, off_colour, y_offset)
    lights = [
        ("red",    LIGHT_RED_ON,    LIGHT_RED_OFF,    -25),
        ("yellow", LIGHT_YELLOW_ON, LIGHT_YELLOW_OFF,   0),
        ("green",  LIGHT_GREEN_ON,  LIGHT_GREEN_OFF,   25),
    ]

    for name, color_on, color_off, dy in lights:
        cx, cy = x, y + dy         # Centre of this particular circle

        if name == active:
            # ── Active light: bright + glow halo ──
            glow = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color_on, 50), (20, 20), 20)
            screen.blit(glow, (cx - 20, cy - 20))
            pygame.draw.circle(screen, color_on, (cx, cy), 9)
        else:
            # ── Inactive light: dim ──
            pygame.draw.circle(screen, color_off, (cx, cy), 9)


def draw_vehicles(screen, vehicles):
    """
    Draw every vehicle as a direction-aware rounded rectangle with headlights.

    - N / S cars are drawn taller   (16 × 24 px)
    - E / W cars are drawn wider    (24 × 16 px)
    - Each car uses its own randomly-assigned colour
    - Tiny "headlight" dots are drawn at the front of the car

    Args:
        screen:           Pygame display surface
        vehicles (list):  List of VehicleGraphic objects
    """
    for v in vehicles:
        x, y = v.get_coordinates()

        # Skip off-screen vehicles
        if x < -30 or x > ROAD_W + 30 or y < -30 or y > ROAD_H + 30:
            continue

        # Size depends on travel direction
        if v.direction in ('N', 'S'):
            car_rect = pygame.Rect(x, y, 16, 24)       # Tall
        else:
            car_rect = pygame.Rect(x, y, 24, 16)       # Wide

        # Car body (rounded rectangle)
        pygame.draw.rect(screen, v.color, car_rect, border_radius=4)
        # Darker border for a 3-D look
        darker = tuple(max(0, c - 40) for c in v.color)
        pygame.draw.rect(screen, darker, car_rect, 1, border_radius=4)

        # Tiny headlights (warm-white dots at the front)
        hl = (240, 240, 200)
        if v.direction == 'S':
            pygame.draw.circle(screen, hl, (x + 4,  y + 22), 2)
            pygame.draw.circle(screen, hl, (x + 12, y + 22), 2)
        elif v.direction == 'N':
            pygame.draw.circle(screen, hl, (x + 4,  y + 2), 2)
            pygame.draw.circle(screen, hl, (x + 12, y + 2), 2)
        elif v.direction == 'E':
            pygame.draw.circle(screen, hl, (x + 22, y + 4), 2)
            pygame.draw.circle(screen, hl, (x + 22, y + 12), 2)
        elif v.direction == 'W':
            pygame.draw.circle(screen, hl, (x + 2, y + 4), 2)
            pygame.draw.circle(screen, hl, (x + 2, y + 12), 2)


def draw_direction_labels(screen, font):
    """
    Draw compass labels (N, S, E, W) at the edges of each road
    so the user knows which direction is which.
    """
    mid_x, mid_y = ROAD_W // 2, ROAD_H // 2
    for text, lx, ly in [('N', mid_x - 5, 15),
                          ('S', mid_x - 5, ROAD_H - 30),
                          ('E', ROAD_W - 80, mid_y - 8),
                          ('W', 60, mid_y - 8)]:
        screen.blit(font.render(text, True, TEXT_SECONDARY), (lx, ly))


# =============================================================================
# DASHBOARD PANEL — The right-hand stats / controls area
# =============================================================================

def draw_stats_panel(screen, env, phase, phase_time, last_action,
                     nodes_expanded, speed_idx, paused, fonts):
    """
    Draw the information dashboard on the right side of the window.

    Sections (top to bottom):
        1. Title
        2. Signal status  (which direction is green, timer, AI decision)
        3. Queue bar chart (visual bars for N / S / E / W waiting cars)
        4. Live statistics (vehicles served, wait time, throughput)
        5. Speed / pause indicator
        6. Controls help   (keyboard shortcuts)

    Args:
        screen:             Pygame surface
        env:                IntersectionEnvironment instance
        phase (int):        Current signal phase
        phase_time (int):   Seconds the current phase has been active
        last_action (str):  Last AI decision string
        nodes_expanded (int): States explored by A* last run
        speed_idx (int):    Index into SPEED_OPTIONS
        paused (bool):      Is the simulation paused?
        fonts (dict):       {'title': ..., 'body': ..., 'small': ...}
    """
    px = ROAD_W    # Panel starts where the road area ends

    # ── Background ─────────────────────────────────────────────────
    pygame.draw.rect(screen, PANEL_BG, (px, 0, PANEL_W, SCREEN_H))
    pygame.draw.line(screen, PANEL_BORDER, (px, 0), (px, SCREEN_H), 2)

    # ── Title ──────────────────────────────────────────────────────
    ty = 20
    screen.blit(fonts['title'].render("Traffic AI", True, ACCENT_GREEN),
                (px + 20, ty))
    screen.blit(fonts['small'].render("A* Search Controller", True, TEXT_SECONDARY),
                (px + 20, ty + 30))

    # ── Divider ────────────────────────────────────────────────────
    dy = ty + 55
    pygame.draw.line(screen, PANEL_BORDER,
                     (px + 15, dy), (px + PANEL_W - 15, dy), 1)

    # ── Signal Status ──────────────────────────────────────────────
    sy = dy + 12
    screen.blit(fonts['small'].render("SIGNAL STATUS", True, TEXT_SECONDARY),
                (px + 20, sy))
    sy += 24

    # Determine display text and colour for the current phase
    if phase == ai.PHASE_NS:
        status_text, status_color = "N-S GREEN", LIGHT_GREEN_ON
    elif phase == ai.PHASE_EW:
        status_text, status_color = "E-W GREEN", LIGHT_GREEN_ON
    else:
        status_text, status_color = "YELLOW", LIGHT_YELLOW_ON

    # Coloured dot + label
    pygame.draw.circle(screen, status_color, (px + 30, sy + 8), 6)
    screen.blit(fonts['body'].render(status_text, True, TEXT_PRIMARY),
                (px + 45, sy))
    sy += 24
    screen.blit(fonts['body'].render(f"Phase Timer: {phase_time}s", True, TEXT_PRIMARY),
                (px + 20, sy))
    sy += 22
    screen.blit(fonts['body'].render(f"AI Decision: {last_action}", True, TEXT_ACCENT),
                (px + 20, sy))
    sy += 22
    screen.blit(fonts['small'].render(f"Nodes explored: {nodes_expanded}", True, TEXT_SECONDARY),
                (px + 20, sy))

    # ── Divider ────────────────────────────────────────────────────
    sy += 25
    pygame.draw.line(screen, PANEL_BORDER,
                     (px + 15, sy), (px + PANEL_W - 15, sy), 1)

    # ── Queue Bar Chart ────────────────────────────────────────────
    sy += 12
    screen.blit(fonts['small'].render("QUEUE LEVELS", True, TEXT_SECONDARY),
                (px + 20, sy))
    sy += 24

    bar_max_w = 180     # Max bar width in pixels
    bar_h = 18          # Bar height
    bar_gap = 8         # Gap between bars
    max_q = max(max(env.queues.values()), 1)   # For scaling (avoid ÷ 0)

    for lane in ['N', 'S', 'E', 'W']:
        q = int(env.queues[lane])
        bar_w = max(2, int((q / max(max_q, 5)) * bar_max_w))

        # Lane label
        screen.blit(fonts['body'].render(f"{lane}:", True, TEXT_PRIMARY),
                    (px + 20, sy))
        # Background bar
        pygame.draw.rect(screen, (40, 43, 52),
                         (px + 50, sy + 2, bar_max_w, bar_h), border_radius=4)
        # Filled bar
        pygame.draw.rect(screen, QUEUE_COLORS[lane],
                         (px + 50, sy + 2, bar_w, bar_h), border_radius=4)
        # Count label
        screen.blit(fonts['small'].render(str(q), True, TEXT_PRIMARY),
                    (px + 50 + bar_max_w + 10, sy + 2))
        sy += bar_h + bar_gap

    # ── Divider ────────────────────────────────────────────────────
    sy += 8
    pygame.draw.line(screen, PANEL_BORDER,
                     (px + 15, sy), (px + PANEL_W - 15, sy), 1)

    # ── Live Statistics ────────────────────────────────────────────
    sy += 12
    screen.blit(fonts['small'].render("LIVE STATISTICS", True, TEXT_SECONDARY),
                (px + 20, sy))
    sy += 24

    stats = [
        ("Vehicles Served", str(env.total_served)),
        ("Avg Wait Time",   f"{env.get_avg_wait_seconds():.1f}s"),
        ("Throughput",      f"{env.get_throughput_per_minute():.1f} cars/min"),
        ("Active Vehicles", str(len(env.vehicles))),
    ]
    for label, value in stats:
        screen.blit(fonts['body'].render(label, True, TEXT_SECONDARY),
                    (px + 20, sy))
        screen.blit(fonts['body'].render(value, True, ACCENT_BLUE),
                    (px + 200, sy))
        sy += 22

    # ── Divider ────────────────────────────────────────────────────
    sy += 12
    pygame.draw.line(screen, PANEL_BORDER,
                     (px + 15, sy), (px + PANEL_W - 15, sy), 1)

    # ── Speed / Pause ──────────────────────────────────────────────
    sy += 12
    speed_val = SPEED_OPTIONS[speed_idx]
    speed_text = f"Speed: {speed_val}x"
    if paused:
        speed_text += "  [PAUSED]"
    screen.blit(fonts['body'].render(
        speed_text, True,
        LIGHT_YELLOW_ON if paused else TEXT_PRIMARY), (px + 20, sy))

    # ── Controls (pinned near bottom) ──────────────────────────────
    cy = SCREEN_H - 170
    pygame.draw.line(screen, PANEL_BORDER,
                     (px + 15, cy), (px + PANEL_W - 15, cy), 1)
    cy += 12
    screen.blit(fonts['small'].render("CONTROLS", True, TEXT_SECONDARY),
                (px + 20, cy))
    cy += 22
    for line in ["N/S/E/W  Spawn car",
                 "P        Pause / Resume",
                 "H        Toggle help",
                 "+/-      Change speed",
                 "Q/ESC    Quit"]:
        screen.blit(fonts['small'].render(line, True, TEXT_SECONDARY),
                    (px + 20, cy))
        cy += 18


# =============================================================================
# OVERLAYS — Help screen and pause indicator
# =============================================================================

def draw_help_overlay(screen, fonts):
    """
    Semi-transparent overlay explaining the simulation.
    Toggled with the H key.
    """
    # Dark translucent backdrop
    overlay = pygame.Surface((ROAD_W, ROAD_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    lines = [
        ("How This Works",                                    ACCENT_GREEN,  'title'),
        ("",                                                  None,          'gap'),
        ("This simulation uses the A* Search Algorithm to",   TEXT_PRIMARY,  'body'),
        ("control traffic signals at a 4-way intersection.",  TEXT_PRIMARY,  'body'),
        ("",                                                  None,          'gap'),
        ("The AI looks 5 steps into the future to decide",    TEXT_PRIMARY,  'body'),
        ("whether to KEEP the current green or SWITCH it,",   TEXT_PRIMARY,  'body'),
        ("minimizing total waiting time for all vehicles.",    TEXT_PRIMARY,  'body'),
        ("",                                                  None,          'gap'),
        ("Keyboard Controls:",                                TEXT_ACCENT,   'body'),
        ("  N / S / E / W  —  Spawn a car",                  TEXT_PRIMARY,  'body'),
        ("  P              —  Pause / Resume",                TEXT_PRIMARY,  'body'),
        ("  H              —  Close this help",               TEXT_PRIMARY,  'body'),
        ("  + / -          —  Speed up / Slow down",          TEXT_PRIMARY,  'body'),
        ("  Q / ESC        —  Quit",                          TEXT_PRIMARY,  'body'),
        ("",                                                  None,          'gap'),
        ("Press H to close this overlay",                     TEXT_SECONDARY,'small'),
    ]

    y = 150
    for text, color, style in lines:
        if style == 'gap':
            y += 15
            continue
        surf = fonts[style].render(text, True, color)
        screen.blit(surf, ((ROAD_W - surf.get_width()) // 2, y))
        y += 40 if style == 'title' else 26


def draw_pause_overlay(screen, fonts):
    """Draw a 'PAUSED' banner over the road area."""
    overlay = pygame.Surface((ROAD_W, ROAD_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 100))
    screen.blit(overlay, (0, 0))

    text = fonts['title'].render("PAUSED", True, LIGHT_YELLOW_ON)
    screen.blit(text, ((ROAD_W - text.get_width()) // 2,
                       (ROAD_H - text.get_height()) // 2))

    sub = fonts['body'].render("Press P to resume", True, TEXT_SECONDARY)
    screen.blit(sub, ((ROAD_W - sub.get_width()) // 2,
                      ROAD_H // 2 + 40))


# =============================================================================
# MAIN GAME LOOP
# =============================================================================

def main():
    """
    Sets up everything and runs the simulation loop.

    The game loop runs at 60 FPS (frames per second). Each frame it:
        1. Handles keyboard / window input
        2. Updates the simulation (moves cars, runs AI)
        3. Draws everything to the screen
        4. Waits to maintain 60 FPS
    """
    # ── Initialise Pygame ──────────────────────────────────────────
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE | pygame.SCALED)
    pygame.display.set_caption("AI Traffic Signal Controller — A* Search Engine")
    clock = pygame.time.Clock()

    # ── Fonts (different sizes for different UI areas) ─────────────
    fonts = {
        'title': pygame.font.SysFont("Segoe UI", 28, bold=True),
        'body':  pygame.font.SysFont("Segoe UI", 15),
        'small': pygame.font.SysFont("Consolas", 13),
    }

    # ── Simulation state ───────────────────────────────────────────
    env = IntersectionEnvironment()         # The virtual intersection world

    phase = ai.PHASE_NS                    # Start with N-S green
    phase_time = 0                         # Timer for current phase
    last_green = ai.PHASE_NS              # Remember who had green last
    last_action = "KEEP"                   # Latest AI decision
    nodes_expanded = 0                     # A* search stats
    frame_counter = 0                      # Total frames elapsed

    # ── UI state ───────────────────────────────────────────────────
    paused = False                         # Simulation paused?
    show_help = False                      # Help overlay visible?
    speed_idx = 0                          # Index into SPEED_OPTIONS

    # =================================================================
    # THE MAIN LOOP — runs once per frame (~60 times per second)
    # =================================================================
    while True:
        speed = SPEED_OPTIONS[speed_idx]

        # ── Step 1: Handle user input ──────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                # Spawn cars
                if   event.key == pygame.K_n: env.force_spawn('N')
                elif event.key == pygame.K_s: env.force_spawn('S')
                elif event.key == pygame.K_e: env.force_spawn('E')
                elif event.key == pygame.K_w: env.force_spawn('W')

                # Pause / resume
                elif event.key == pygame.K_p:
                    paused = not paused

                # Help overlay
                elif event.key == pygame.K_h:
                    show_help = not show_help

                # Speed controls
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS,
                                   pygame.K_KP_PLUS):
                    speed_idx = min(speed_idx + 1, len(SPEED_OPTIONS) - 1)
                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE,
                                   pygame.K_KP_MINUS):
                    speed_idx = max(speed_idx - 1, 0)

                # Quit
                elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
        # ── Step 2: Update simulation (skipped when paused) ────────
        if not paused:
            for _ in range(speed):              # Repeat for speed multiplier
                frame_counter += 1

                # Random traffic every ~0.75 seconds
                if frame_counter % 45 == 0:
                    env.process_ambient_flow()

                # AI decision every ~1 second (60 frames)
                if frame_counter % 60 == 0:
                    phase_time += 1

                    # Ask A* for the optimal action
                    last_action, nodes_expanded = ai.compute_astar_action(
                        env.queues, phase, phase_time, last_green
                    )

                    # Apply the decision
                    if last_action == "SWITCH":
                        last_green = phase
                        phase = ai.PHASE_YELLOW
                        phase_time = 0
                    elif last_action == "TO_GREEN":
                        phase = (ai.PHASE_EW if last_green == ai.PHASE_NS
                                 else ai.PHASE_NS)
                        phase_time = 0

                # Move all cars
                env.update_physics(phase)

        # ── Step 3: Draw everything ────────────────────────────────

        # 3a – Background & roads
        screen.fill(BG_COLOR)
        draw_grid_background(screen)
        draw_roads(screen)

        # 3b – Traffic lights at the four corners of the intersection
        mid_x, mid_y = ROAD_W // 2, ROAD_H // 2

        if phase == ai.PHASE_NS:
            ns_light, ew_light = "green", "red"
        elif phase == ai.PHASE_EW:
            ns_light, ew_light = "red", "green"
        else:   # YELLOW
            ns_light = "yellow" if last_green == ai.PHASE_NS else "red"
            ew_light = "yellow" if last_green == ai.PHASE_EW else "red"

        draw_traffic_light(screen, mid_x - 85, mid_y - 85, ns_light)
        draw_traffic_light(screen, mid_x + 85, mid_y + 85, ns_light)
        draw_traffic_light(screen, mid_x + 85, mid_y - 85, ew_light)
        draw_traffic_light(screen, mid_x - 85, mid_y + 85, ew_light)

        # 3c – Vehicles
        draw_vehicles(screen, env.vehicles)

        # 3d – Direction labels
        draw_direction_labels(screen, fonts['body'])

        # 3e – Dashboard panel
        draw_stats_panel(screen, env, phase, phase_time, last_action,
                         nodes_expanded, speed_idx, paused, fonts)

        # 3f – Overlays
        if paused and not show_help:
            draw_pause_overlay(screen, fonts)
        if show_help:
            draw_help_overlay(screen, fonts)

        # ── Step 4: Flip the display buffer & cap FPS ──────────────
        pygame.display.flip()
        clock.tick(60)


# =============================================================================
# ENTRY POINT — Python starts executing here
# =============================================================================
if __name__ == "__main__":
    main()