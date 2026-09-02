# agent.py
import random
from collections import deque
import heapq


class GreedyGridAgent:
    """A simple agent that tries to move around systematically to clear the grid."""

    def __init__(self):
        self.actions_pool = ['Up', 'Down', 'Left', 'Right']

    def sense_and_act(self, percept: dict) -> str:
        # If standing directly on food, or just wander / move towards coordinates
        pos = percept['agent_pos']
        # Simple heuristic or fallback random sweep
        return random.choice(self.actions_pool)
    
class SimpleReflexAgent:
    """Chooses actions using only the current percept."""

    def sense_and_act(self, percept: dict) -> str:
        if percept ['food_here']:
            return 'Suck'

        if percept['wall_ahead']:
            return 'TurnLeft'

        return 'MoveForward'

class ModelBasedAgent:
    """Maintains an internal model despite receiving only local percepts."""

    DIRECTION_CHANGES = {
        'Up': (0, 1),
        'Right': (1, 0),
        'Down': (0, -1),
        'Left': (-1, 0)
    }

    LEFT_TURN = {
        'Up': 'Left',
        'Left': 'Down',
        'Down': 'Right',
        'Right': 'Up'
    }

    RIGHT_TURN = {
        'Up': 'Right',
        'Right': 'Down',
        'Down': 'Left',
        'Left': 'Up'
    }

    def __init__(self):
        self.relative_pos = (0, 0)
        self.facing = 'Up'

        self.visited_cells = {(0, 0)}
        self.known_walls = set()

        self.percept_history = []
        self.action_history = []

        self.last_action = None
        self.last_percept = None
        self.turns_without_moving = 0

    def _cell_ahead(self):
        dx, dy = self.DIRECTION_CHANGES[self.facing]

        return (
            self.relative_pos[0] + dx,
            self.relative_pos[1] + dy
        )

    def _update_state_from_last_action(self):
        """Transition model: predict the result of the previous action."""

        if self.last_action == 'TurnLeft':
            self.facing = self.LEFT_TURN[self.facing]

        elif self.last_action == 'TurnRight':
            self.facing = self.RIGHT_TURN[self.facing]

        elif (
            self.last_action == 'MoveForward'
            and self.last_percept is not None
            and not self.last_percept['wall_ahead']
        ):
            self.relative_pos = self._cell_ahead()
            self.visited_cells.add(self.relative_pos)

    def _record_action(self, action, percept):
        self.last_action = action
        self.last_percept = dict(percept)
        self.action_history.append(action)

        if action in ('TurnLeft', 'TurnRight'):
            self.turns_without_moving += 1
        elif action == 'MoveForward':
            self.turns_without_moving = 0

        return action

    def sense_and_act(self, percept: dict) -> str:
        # First update the internal state using the previous action.
        self._update_state_from_last_action()

        # Record the current sensor information.
        self.percept_history.append(dict(percept))

        ahead = self._cell_ahead()

        # Sensor model: interpret wall_ahead as a wall at a relative cell.
        if percept['wall_ahead']:
            self.known_walls.add(ahead)

        if percept['food_here']:
            return self._record_action('Suck', percept)

        if percept['wall_ahead']:
            if self.last_action == 'TurnRight':
                return self._record_action('TurnLeft', percept)
            return self._record_action('TurnRight', percept)

        # Prefer unexplored cells.
        if ahead not in self.visited_cells:
            return self._record_action('MoveForward', percept)

        # After inspecting several directions, permit backtracking through
        # a visited cell so the agent does not become stuck while turning.
        if self.turns_without_moving >= 3:
            return self._record_action('MoveForward', percept)

        return self._record_action('TurnRight', percept)

class SearchAgent:
    """Plans complete paths using uninformed graph-search algorithms."""

    ACTIONS = (
        ('Up', (0, 1)),
        ('Down', (0, -1)),
        ('Left', (-1, 0)),
        ('Right', (1, 0))
    )

    def __init__(self, active_algo='BFS'):
        self.active_algo = active_algo
        self.plan = []

    def _get_neighbors(self, position, walls, grid_size):
        """Generate valid action-state pairs from one grid position."""

        width, height = grid_size
        x, y = position
        neighbors = []

        for action, (dx, dy) in self.ACTIONS:
            next_position = (x + dx, y + dy)

            inside_grid = (
                0 <= next_position[0] < width
                and 0 <= next_position[1] < height
            )

            if inside_grid and next_position not in walls:
                neighbors.append((action, next_position))

        return neighbors

    def bfs_search(
        self,
        start_pos,
        goal_pos,
        walls,
        grid_size
    ):
        """Breadth-first graph search using a FIFO queue."""

        start = tuple(start_pos)
        goal = tuple(goal_pos)
        wall_set = {tuple(wall) for wall in walls}

        frontier = deque([(start, [])])
        reached = {start}

        while frontier:
            current_pos, path_taken = frontier.popleft()

            if current_pos == goal:
                return path_taken

            for action, next_pos in self._get_neighbors(
                current_pos,
                wall_set,
                grid_size
            ):
                if next_pos not in reached:
                    reached.add(next_pos)
                    frontier.append(
                        (next_pos, path_taken + [action])
                    )

        return None

    def dfs_search(
        self,
        start_pos,
        goal_pos,
        walls,
        grid_size
    ):
        """Depth-first graph search using a LIFO stack."""

        start = tuple(start_pos)
        goal = tuple(goal_pos)
        wall_set = {tuple(wall) for wall in walls}

        frontier = [(start, [])]
        reached = {start}

        while frontier:
            current_pos, path_taken = frontier.pop()

            if current_pos == goal:
                return path_taken

            neighbors = self._get_neighbors(
                current_pos,
                wall_set,
                grid_size
            )

            # Reverse insertion preserves the ACTIONS priority when popping.
            for action, next_pos in reversed(neighbors):
                if next_pos not in reached:
                    reached.add(next_pos)
                    frontier.append(
                        (next_pos, path_taken + [action])
                    )

        return None

    def ucs_search(
        self,
        start_pos,
        goal_pos,
        walls,
        grid_size
    ):
        """Uniform-cost graph search ordered by total path cost g(n)."""

        start = tuple(start_pos)
        goal = tuple(goal_pos)
        wall_set = {tuple(wall) for wall in walls}

        frontier = [(0, start, [])]
        reached = set()
        best_cost = {start: 0}

        while frontier:
            path_cost, current_pos, path_taken = heapq.heappop(
                frontier
            )

            if current_pos in reached:
                continue

            if current_pos == goal:
                return path_taken

            reached.add(current_pos)

            for action, next_pos in self._get_neighbors(
                current_pos,
                wall_set,
                grid_size
            ):
                new_cost = path_cost + 1

                if (
                    next_pos not in reached
                    and new_cost < best_cost.get(
                        next_pos,
                        float('inf')
                    )
                ):
                    best_cost[next_pos] = new_cost

                    heapq.heappush(
                        frontier,
                        (
                            new_cost,
                            next_pos,
                            path_taken + [action]
                        )
                    )

        return None

    def _run_selected_search(
        self,
        start_pos,
        goal_pos,
        walls,
        grid_size
    ):
        search_methods = {
            'BFS': self.bfs_search,
            'DFS': self.dfs_search,
            'UCS': self.ucs_search
        }

        if self.active_algo not in search_methods:
            raise ValueError(
                f"Unknown search algorithm: {self.active_algo}"
            )

        return search_methods[self.active_algo](
            start_pos,
            goal_pos,
            walls,
            grid_size
        )

    def sense_and_act(self, percept: dict) -> str:
        # Food collection is still a reactive action.
        if percept['food_here']:
            self.plan = []
            return 'Suck'

        if not self.plan:
            start_pos = tuple(percept['agent_pos'])
            walls = percept['walls']
            grid_size = percept['grid_size']
            food_positions = [
                tuple(food)
                for food in percept['all_food']
            ]

            if not food_positions:
                return 'NoOp'

            # Try nearer food first. If one is unreachable,
            # continue to the next candidate.
            ordered_goals = sorted(
                food_positions,
                key=lambda food: (
                    abs(start_pos[0] - food[0])
                    + abs(start_pos[1] - food[1])
                )
            )

            for goal_pos in ordered_goals:
                possible_plan = self._run_selected_search(
                    start_pos,
                    goal_pos,
                    walls,
                    grid_size
                )

                if possible_plan is not None:
                    self.plan = possible_plan
                    break

        if self.plan:
            return self.plan.pop(0)

        return 'NoOp'
