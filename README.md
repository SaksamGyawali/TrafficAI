# 🚦 AI Traffic Signal Controller

An intelligent traffic signal simulation powered by the **A\* Search Algorithm**. Watch as the AI plans several steps ahead to minimize waiting time at a 4-way intersection — just like a chess engine thinking multiple moves ahead!

Built with **Python** and **Pygame**.

---

## ✨ Features

| Feature | Description |
|---|---|
| **A\* Search AI** | Looks 5 steps into the future to find the optimal signal timing |
| **Real-time Dashboard** | Live stats: throughput, wait time, queue levels, and AI decision info |
| **Visual Simulation** | Multi-lane roads, crosswalks, direction-aware vehicles with headlights |
| **3-Light Signals** | Realistic traffic light housings with glow effects |
| **Speed Control** | Run at 1×, 2×, or 4× speed to see the AI work faster |
| **Pause & Help** | Pause anytime, or read the built-in help overlay |
| **Interactive Spawning** | Press N/S/E/W to manually add cars from any direction |
| **Colourful Vehicles** | Cars spawn in random colours from a curated palette |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** — [Download Python](https://www.python.org/downloads/)
- **Pygame 2.5+** — installed automatically via the command below

### Installation

```bash
# 1. Clone or download this project
git clone https://github.com/Saksam/AIProject.git
cd AIProject

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the simulation
python main.py
```

---

## 🎮 Controls

| Key | Action |
|-----|--------|
| `N` | Spawn a car from the **North** |
| `S` | Spawn a car from the **South** |
| `E` | Spawn a car from the **East** |
| `W` | Spawn a car from the **West** |
| `P` | **Pause** / Resume the simulation |
| `H` | Toggle the **Help** overlay |
| `+` / `=` | **Speed up** (1× → 2× → 4×) |
| `-` / `_` | **Slow down** (4× → 2× → 1×) |
| `Q` / `ESC` | **Quit** |

---

## 🧠 How the Simulation and AI Work

This project combines a physics-based simulation with a classical search algorithm. Here is a detailed breakdown of what is happening under the hood.

### 1. The Virtual World (Simulation)
The environment (`simulation.py`) manages the road and the cars. 
- **Vehicle Movement**: Instead of moving by raw pixels, each car has a `progress` value from `0.0` to `1.0`. `0.0` means it just spawned off-screen, `0.42` means it is entering the intersection, and `1.0` means it has driven off the other side.
- **Queueing Physics**: Every frame, a car tries to move forward. It will stop if:
  1. The light is RED and it has reached the "stop line" (progress `0.40`).
  2. There is another car directly in front of it (collision avoidance).
  Cars stack up behind the red light automatically because each subsequent car calculates a safe stopping distance behind the car in front of it.
- **Crossing**: When a car's progress passes `0.42`, it crosses the line. The simulation counts it as "served", removes it from the waiting queue, and shifts all trailing cars forward in the queue index.

### 2. The Brain (A* Search Algorithm)
The traffic controller (`ai_engine.py`) uses the **A* Search Algorithm** to decide when to change the lights. Every second, the AI takes a snapshot of the intersection and plans up to 5 steps into the future.

Here is how the AI "thinks":
1. **The State**: It looks at the current phase (e.g., East-West Green), how long it's been green, and how many cars are waiting in each direction.
2. **Branching Futures**: It considers its options:
   - Option A: **KEEP** the light green.
   - Option B: **SWITCH** the light to yellow.
3. **Simulating Time**: For every option, it creates a hypothetical future (a `SearchState`). It subtracts cars from the green lanes and calculates the "Cost".
   - **Cost** = (Total cars waiting) × (Time spent waiting).
4. **Looking Deeper**: It repeats this branching process from the new hypothetical states, looking up to 5 steps ahead. 
5. **The Heuristic**: To avoid exploring millions of useless futures, A* uses a "heuristic" (an educated guess). It squares the number of waiting cars to heavily penalize massive traffic jams. This helps the AI quickly discard bad ideas.
6. **The Decision**: After exploring the tree of futures, it finds the sequence of actions that results in the lowest total waiting time. It then executes *only the first action* of that sequence and waits for the next second to re-evaluate (this is called "Receding Horizon Control").

### 3. The "Stuck on Green" Bug (Resolved)
Before a recent fix, the AI suffered from a fascinating logic bug: it would sometimes leave the light green for over 800 seconds while hundreds of cars waited on the red light! 
- **Why?** When the AI simulated the future, it simulated switching to yellow. But for the step *after* yellow, it suffered from "amnesia" and forgot which direction it came from. 
- **The Result**: The AI simulated going: `East-West Green` → `Yellow` → `East-West Green`. Since this sequence just wasted 5 seconds of yellow light without clearing any traffic, the AI logically deduced that "Switching is a terrible idea" and chose to keep the light green forever!
- **The Fix**: We gave the `SearchState` memory of the `last_green` light. Now, the AI correctly anticipates that `East-West` → `Yellow` leads to `North-South Green`, allowing it to accurately value switching the lights to clear massive queues.

### Key AI Parameters

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `STEP_SIZE` | 5 | Each lookahead step = 5 seconds of simulation time |
| `SATURATION_FLOW` | 2 | Max cars served per lane per step |
| `MIN_GREEN_TIME` | 15 | Minimum green light duration (safety rule) |
| Search Depth | 5 | AI looks 5 steps into the future |

---

## 📁 Project Structure

```
AIProject/
├── main.py              # Entry point — window, rendering, game loop
├── ai_engine.py         # A* search algorithm for signal optimization
├── simulation.py        # Vehicle physics, intersection environment, stats
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## 📊 Dashboard Explained

The right-hand panel shows live data:

- **Signal Status** — Which direction currently has green, phase timer, and the AI's last decision
- **Queue Levels** — Bar chart showing cars waiting in each lane (N / S / E / W)
- **Live Statistics** — Vehicles served, average wait time, throughput (cars/min), and active vehicle count
- **Speed & Controls** — Current simulation speed and keyboard shortcut reference

---

## 🎓 Educational Value

This project demonstrates several Computer Science concepts:

- **A\* Search Algorithm** — optimal pathfinding / decision-making
- **Heuristic Functions** — admissible estimates for search efficiency
- **State Space Search** — exploring a tree of possible futures
- **Object-Oriented Programming** — classes for vehicles and environments
- **Real-time Simulation** — physics loops, frame-rate control
- **Data Visualisation** — bar charts and live statistics

---

## 📝 License

This project is open-source. Feel free to use, modify, and share!
