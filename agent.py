# agent.py
import random

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
            return self._record_action('TurnRight', percept)

        # Prefer unexplored cells.
        if ahead not in self.visited_cells:
            return self._record_action('MoveForward', percept)

        # After inspecting several directions, permit backtracking through
        # a visited cell so the agent does not become stuck while turning.
        if self.turns_without_moving >= 3:
            return self._record_action('MoveForward', percept)

        return self._record_action('TurnRight', percept)