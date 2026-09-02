import random
import tkinter as tk
from agent import SimpleReflexAgent, ModelBasedAgent, SearchAgent


class VisualGridHuntGame:
    """A flexible Pacman-style grid environment with support for configurable opponents and larger scales."""

    def __init__(self, width=10, height=10, num_food=10, num_opponents=2, custom_walls=None):
        if width < 1 or height < 1:
            raise ValueError('width and height must be positive')
        if num_food < 0 or num_opponents < 0:
            raise ValueError('num_food and num_opponents cannot be negative')

        self.width = width
        self.height = height
        self.agent_pos = [0, 0]  # Starting position (x, y)
        self.agent_facing = 'Up'

        if custom_walls is not None:
            self.walls = set()
            for wall in custom_walls:
                try:
                    if len(wall) != 2:
                        continue
                    x, y = wall
                except (TypeError, ValueError):
                    continue
                if (
                    isinstance(x, int)
                    and isinstance(y, int)
                    and 0 <= x < width
                    and 0 <= y < height
                    and (x, y) != (0, 0)
                ):
                    self.walls.add((x, y))
        else:
            # Generate some default scattered walls for a larger grid
            self.walls = {
                cell for cell in {(2, 2), (2, 3), (5, 5), (6, 5), (3, 7)}
                if cell != (0, 0) and cell[0] < width and cell[1] < height
            }

        free_cells = [
            (x, y)
            for x in range(width)
            for y in range(height)
            if (x, y) != (0, 0) and (x, y) not in self.walls
        ]
        if num_food + num_opponents > len(free_cells):
            raise ValueError('Not enough free cells for food and opponents')

        # Choose positions without retry loops (which could otherwise never finish).
        random.shuffle(free_cells)
        self.food_positions = set(free_cells[:num_food])
        free_cells = free_cells[num_food:]

        # Generate adversarial opponents
        self.opponents = [list(position) for position in free_cells[:num_opponents]]

        # Generate toxic traps in currently unoccupied cells
        self.toxic_traps = set()

        occupied_cells = (
            self.walls
            | self.food_positions
            | {tuple(opponent) for opponent in self.opponents}
            | {(0, 0)}
        )

        available_cells = [
            (x, y)
            for x in range(self.width)
            for y in range(self.height)
            if (x, y) not in occupied_cells
        ]

        num_traps = min(5, len(available_cells))
        self.toxic_traps.update(
            random.sample(available_cells, num_traps)
        )

        self.score = 0
        self.steps = 0
        self.collision = False

    def get_cell_ahead(self):
        """Return the coordinate immediately in front of the agent."""
        direction_changes = {
            'Up': (0, 1),
            'Right': (1, 0),
            'Down': (0, -1),
            'Left': (-1, 0),
        }

        dx, dy = direction_changes.get(self.agent_facing, (0, 0))

        return (
            self.agent_pos[0] + dx,
            self.agent_pos[1] + dy,
        )

    def get_percept(self) -> dict:
        ahead_x, ahead_y = self.get_cell_ahead()

        outside_grid = (
            ahead_x < 0
            or ahead_x >= self.width
            or ahead_y < 0
            or ahead_y >= self.height
        )

        wall_ahead = (
            outside_grid
            or (ahead_x, ahead_y) in self.walls
        )

        return {
            # Local information retained from Practical 2
            'wall_ahead': wall_ahead,
            'food_here': tuple(self.agent_pos) in self.food_positions,
            'smells_toxin': tuple(self.agent_pos) in self.toxic_traps,

            # Global search model required by Practical 3
            'agent_pos': list(self.agent_pos),
            'grid_size': (self.width, self.height),
            'walls': list(self.walls),
            'all_food': list(self.food_positions),
            'remaining_food': len(self.food_positions)
        }

    def execute_action(self, action: str):
        self.steps += 1
        moved = False
        turns = {
            'TurnLeft': {'Up': 'Left', 'Left': 'Down', 'Down': 'Right', 'Right': 'Up'},
            'TurnRight': {'Up': 'Right', 'Right': 'Down', 'Down': 'Left', 'Left': 'Up'},
        }
        if action in turns:
            self.agent_facing = turns[action][self.agent_facing]

        elif action in ('Up', 'Down', 'Left', 'Right'):
            direction_changes = {
                'Up': (0, 1),
                'Down': (0, -1),
                'Left': (-1, 0),
                'Right': (1, 0)
            }

            dx, dy = direction_changes[action]
            new_x = self.agent_pos[0] + dx
            new_y = self.agent_pos[1] + dy

            valid_position = (
                0 <= new_x < self.width
                and 0 <= new_y < self.height
                and (new_x, new_y) not in self.walls
            )

            if valid_position:
                self.agent_pos = [new_x, new_y]
                self.agent_facing = action
                moved = True
            else:
                self.score -= 5

        elif action == 'MoveForward':
            new_x, new_y = self.get_cell_ahead()
            if (
                0 <= new_x < self.width
                and 0 <= new_y < self.height
                and (new_x, new_y) not in self.walls
            ):
                self.agent_pos = [new_x, new_y]
                moved = True
            else:
                self.score -= 5
        elif action == 'Suck':
            current_pos = tuple(self.agent_pos)
            if current_pos in self.food_positions:
                self.food_positions.remove(current_pos)
                self.score += 20

        elif action == 'NoOp':
            pass  # Do nothing

        else:
            raise ValueError(f"Unknown action: {action}")

        if moved and tuple(self.agent_pos) in self.toxic_traps:
            self.score -= 15

        # Check for a collision before moving opponents as well as after they move.
        # This catches the case where the agent moves onto an opponent.
        if any(opponent == self.agent_pos for opponent in self.opponents):
            self.score -= 50
            self.collision = True

        for opponent in self.opponents:
            move = random.choice(['Up', 'Down', 'Left', 'Right', 'Stay'])
            candidate = list(opponent)
            if move == 'Up': candidate[1] += 1
            elif move == 'Down': candidate[1] -= 1
            elif move == 'Left': candidate[0] -= 1
            elif move == 'Right': candidate[0] += 1
            if (
                0 <= candidate[0] < self.width
                and 0 <= candidate[1] < self.height
                and tuple(candidate) not in self.walls
            ):
                opponent[:] = candidate
            if opponent == self.agent_pos:
                self.score -= 50
                self.collision = True

    def is_done(self):
        return self.collision or not self.food_positions


class GridGameGUI:
    def __init__(
        self,
        root,
        width=10,
        height=10,
        num_food=12,
        num_opponents=2,
        walls=None,
        agent=None,
    ):
        self.root = root
        self.env = VisualGridHuntGame(
            width=width,
            height=height,
            num_food=num_food,
            num_opponents=num_opponents,
            custom_walls=walls,
        )
        self.agent = agent if agent is not None else SimpleReflexAgent()
        self.canvas = tk.Canvas(root, width=width * 40, height=height * 40)
        self.canvas.pack()
        self.label = tk.Label(root, text='Score: 0 | Steps: 0')
        self.label.pack()
        self.btn = tk.Button(root, text='Start', command=self.run_loop)
        self.btn.pack()
        self.draw_grid()

    def draw_grid(self):
        self.canvas.delete('all')
        for x in range(self.env.width):
            for y in range(self.env.height):
                top = (self.env.height - y - 1) * 40
                fill = 'black' if (x, y) in self.env.walls else 'white'
                self.canvas.create_rectangle(
                    x * 40,
                    top,
                    x * 40 + 40,
                    top + 40,
                    fill=fill,
                )
                if (x, y) in self.env.food_positions:
                    self.canvas.create_oval(
                        x * 40 + 14,
                        top + 14,
                        x * 40 + 26,
                        top + 26,
                        fill='gold',
                    )
                if (x, y) in self.env.toxic_traps:
                    self.canvas.create_polygon(
                        x * 40 + 20, top + 8,
                        x * 40 + 32, top + 32,
                        x * 40 + 8, top + 32,
                        fill='red',
                    )
                if [x, y] in self.env.opponents:
                    self.canvas.create_oval(
                        x * 40 + 8, top + 8,
                        x * 40 + 32, top + 32,
                        fill='green',
                    )
        x, y = self.env.agent_pos
        top = (self.env.height - y - 1) * 40
        self.canvas.create_oval(
            x * 40 + 6,
            top + 6,
            x * 40 + 34,
            top + 34,
            fill='blue',
        )

    def run_loop(self):
        self.btn.config(state="disabled")

        def step():
            if not self.env.is_done():
                percept = self.env.get_percept()
                action = self.agent.sense_and_act(percept)
                if not isinstance(action, str):
                    raise ValueError('Agent must return an action string')
                self.env.execute_action(action)

                self.draw_grid()
                self.label.config(
                    text=(
                        f"Score: {self.env.score} | Steps: {self.env.steps} | "
                        f"Action: {action}"
                    )
                )
                self.root.after(250, step)
            else:
                end_text = (
                    f"Collision! Game Over! Final Score: {self.env.score}"
                    if self.env.collision
                    else f"Finished! Final Score: {self.env.score}"
                )
                self.label.config(text=end_text)
                self.btn.config(state="normal")

        step()

if __name__ == "__main__":
    random.seed(7)

    root = tk.Tk()
    # Try a larger grid size like 12x12 with 15 food and 3 opponents!
    app = GridGameGUI(
        root,
        width=12,
        height=12,
        num_food=15,
        num_opponents=0,
        agent=SearchAgent(active_algo='BFS'),
    )

    root.mainloop()
