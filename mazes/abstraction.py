from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from option import Option, NONE, Some, Result, Ok, Err

import mazes.io
from lib.ds import SimpleQueue


class CellOccupiedState(Enum):
    In_QUEUE = 0,
    OCCUPYING = 1,


class States(Enum):
    MOVE_UP = 1
    MOVE_DOWN = 2
    MOVE_LEFT = 3
    MOVE_RIGHT = 4
    DONE = 5
    FAILED = 6
    SUCCEEDED = 7
    STOPPED = 8
    WAITING = 9
    IS_GOAL = 10


class CellType(Enum):
    START = 0,
    GOAL = 1,
    END = 2,
    REGULAR = 3,
    EMPTY = 4,

    def to_label(self) -> str:
        if self == CellType.START:
            return "Start cell"
        if self == CellType.END:
            return "END cell"
        if self == CellType.GOAL:
            return "GOAL cell"
        if self == CellType.REGULAR:
            return "Regular cell"
        if self == CellType.EMPTY:
            return "Empty cell"


class Direction(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

    def get_opposite(self):
        if self == Direction.RIGHT:
            return Direction.LEFT

        if self == Direction.LEFT:
            return Direction.RIGHT

        if self == Direction.UP:
            return Direction.DOWN

        if self == Direction.DOWN:
            return Direction.UP


@dataclass(init=True, eq=True, order=True)
class Navigator:
    label: str
    id: int
    states: SimpleQueue[States]
    priority: int
    current_cell: Option[Cell]
    visited_cells: set[int]

    def empty_current_cell(self) -> None:
        self.current_cell = NONE

    def set_current_cell(self, hold: Cell) -> None:
        self.current_cell = Some(hold)

    def state_sequence(self) -> list[States]:
        return self.states.elements()

    def consume_next_state(self) -> States:
        return self.states.pop()

    def next_state(self) -> States:
        return self.states.peek()

    def add_state(self, intent: States):
        self.states.push(intent)


@dataclass(eq=True, order=False)
class NavigatorStack:
    stack: list[Navigator]
    finalizedNavigators: int
    iteration_count: int

    def __init__(self, navigators: list[Navigator]):
        self.stack = navigators
        self.finalizedNavigators = 0
        self.iteration_count = 0

        self.stack.sort(key=lambda navigator: navigator.priority, reverse=False)

    def attribute_starting_point_to_navigator(self, starting_points: list[Cell]):
        len_of_points = len(starting_points)

        # get a starting point list
        # make sure the list is as big as the stack, if not make it so (distribute navs "equally" through points)
        # if the cell already is occupied add the nav to the queue of the starting point
        for i, navigator in enumerate(self.stack):
            navigator.set_current_cell(starting_points[i % len_of_points])

    def run_until_end(self) -> None:
        while True:
            next_nav_s: Navigator = None
            next_nav: Result[Option[Navigator], str] = self.next_navigator()
            if next_nav.is_err:
                break
            if next_nav.unwrap().is_none:
                continue
            else:
                next_nav_s = next_nav.unwrap().unwrap()
            # RUN ALL THE BEHAVIOR ??

    def next_navigator(self) -> Result[Option[Navigator], str]:
        """
        Returns available navigators in the stack, as long their Intent is not:
        - DONE
        - WAITING
        - FAILED
        - SUCCEEDED
        """
        if len(self.stack) < 1:
            return Err("no nav in stack")

        index = self.iteration_count
        next_navigator = self.stack[index % len(self.stack)]
        next_nav_state = next_navigator.next_state()

        self.iteration_count += 1

        if next_nav_state in [States.FAILED, States.DONE, States.WAITING, States.SUCCEEDED]:
            if next_nav_state in (States.FAILED, States.DONE):
                self.stack = self.stack[1:]
            return Ok(NONE)

        return Ok(Some(next_navigator))

    def add_to_stack(self, nav: Navigator) -> int:
        self.stack.append(nav)
        return len(self.stack)


@dataclass(eq=True, order=True)
class Cell:
    """Represents a valid, walkable position for a navigator"""
    label: str
    position: (int, int)
    current: Option[Navigator]
    queue: SimpleQueue[Navigator]
    connections: dict[Direction, Cell]

    def __init__(self, label: str, position: (int, int)):
        self.label = label
        self.position = position
        self.current = NONE
        self.queue = SimpleQueue()
        self.connections = dict()

    def push_holder(self, holder: Navigator) -> None:
        if holder.current_cell.is_some:
            print(holder.label + " ALREADY HAS HOLDING")
            return

        holder.set_current_cell(self)
        if self.current.is_none:
            self.current = Some(holder)
            return

        self.queue.push(holder)

    def next_holder(self) -> Option[Navigator]:
        if self.current.is_none:
            if self.queue.has_next():
                self.current = Some(self.queue.pop())
            return NONE

        self.current.unwrap().empty_current_cell()
        return_value = self.current
        if self.queue.has_next():
            self.current = Some(self.queue.pop())
        else:
            self.current = NONE

        return return_value

    def list_connections(self) -> str:
        connections: str = ""
        if Direction.UP in self.connections.keys():
            connections += "^"
        if Direction.DOWN in self.connections.keys():
            connections += "v"
        if Direction.LEFT in self.connections.keys():
            connections += "<"
        if Direction.RIGHT in self.connections.keys():
            connections += ">"
        return connections

    def get_next_in_queue(self) -> Option[Navigator]:
        try:
            next_in_queue = self.queue.pop()
        except IndexError:
            self.current = NONE
            return NONE
        self.current = Some(next_in_queue)
        return self.current

    def add_cel(self, direction: Direction, cell: Cell):
        cell.connections[direction.get_opposite()] = self
        self.connections[direction] = cell

    def add_cel_get_next(self, direction: Direction, cell: Cell) -> Cell:
        self.add_cel(direction, cell)
        return self.connections[direction]

    def get_next(self, direction: Direction) -> Cell:
        if direction in self.connections.keys():
            return self.connections[direction]


class Map:
    starting_cells: list[Cell]
    goal_cels: list[Cell]

    def __init__(self, m: list[list[CellType]]):
        self.starting_cells = list[Cell]()
        self.goal_cels = list[Cell]()
        self.__build_map_from_array(m)

    def __build_map_from_array(self, array: list[list[CellType]]):
        current_cell: Cell | None = None

        for row, elems in enumerate(array):
            for coll, cell in enumerate(elems):
                cell_label = array[row][coll].to_label() + " " + str(row) + " " + str(coll)
                c = Cell(label=cell_label, position=(row, coll))

                if row < len(array):
                    # Check for cells that connect from bellow
                    if row + 1 < len(array):
                        cell_type_bellow = array[row + 1][coll]
                        if cell_type_bellow != CellType.EMPTY:
                            c.add_cel(Direction.DOWN, Cell(label=cell_label, position=(row + 1, coll)))

                if CellType.START.to_label() in c.label:
                    self.starting_cells.append(c)
                if CellType.GOAL.to_label() in c.label:
                    self.goal_cels.append(c)

                # Make the new current cell, the cell added to the right of current cell
                if current_cell is None:
                    current_cell = c
                else:
                    current_cell = current_cell.add_cel_get_next(Direction.RIGHT, c)

    @staticmethod
    def map_from_abstraction(abstraction: list[list[str]]) -> list[list[CellType]]:
        result = list[list[CellType]]()
        for i, row in enumerate(abstraction):
            result.append(list[CellType]())
            for spot in row:
                if spot == "S":
                    result[i].append(CellType.START)
                if spot == "#":
                    result[i].append(CellType.REGULAR)
                if spot == "G":
                    result[i].append(CellType.GOAL)
                if spot == "E":
                    result[i].append(CellType.EMPTY)

        return result


if __name__ == "__main__":
    """ Example Map
    S # # # G
        #
        # # #
    """
    mp = [
        [CellType.START, CellType.REGULAR, CellType.REGULAR, CellType.REGULAR, CellType.GOAL, ],
        [CellType.EMPTY, CellType.EMPTY, CellType.REGULAR, CellType.EMPTY, CellType.EMPTY, ],
        [CellType.EMPTY, CellType.EMPTY, CellType.REGULAR, CellType.REGULAR, CellType.END, ],
    ]
    cells = Map(m=mp)
    abstract = mazes.io.read_from_file("test_1.mz", "/home/ninbo/ws/python/ai/final_project/resources").unwrap()
    x = Map.map_from_abstraction(abstract)
    cls = Map(m=x)
    # print(cls.starting_cells)

    navigator_state = SimpleQueue(
        States.MOVE_RIGHT, States.MOVE_RIGHT, States.DONE, States.MOVE_DOWN,
        States.MOVE_DOWN, States.MOVE_RIGHT, States.MOVE_RIGHT,
    )
    navigator_state_2 = SimpleQueue(
        States.MOVE_RIGHT, States.MOVE_RIGHT, States.MOVE_RIGHT,
        States.MOVE_RIGHT, States.IS_GOAL, States.DONE
    )
    navs: list[Navigator] = [
        Navigator(
            label="First", states=navigator_state, priority=1,
            id=1, current_cell=NONE,
        ),
        Navigator(
            label="Second", states=navigator_state_2, priority=1,
            id=1, current_cell=NONE,
        ),
    ]
    navigator_stack = NavigatorStack(navigators=navs)
    navigator_stack.run_until_end()

    # Get a cell, check all imediate connections for goal,
    # Choose a cell to move to (maybe weigths?)