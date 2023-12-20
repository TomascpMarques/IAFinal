from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from option import Option, NONE, Some, Result, Ok, Err

import lib.randoms
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
    IS_GOAL = 10,
    REACHED_GOAL = 11,
    MOVING = 12,


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


@dataclass(eq=True, order=True)
class Navigator:
    label: str
    id: int
    states: SimpleQueue[States]
    priority: int
    current_cell: Option[Cell]
    visited_cells_positions: set[(int, int)]
    goals: set[(int, int)]
    queued_cells: SimpleQueue[Cell]

    def __init__(self, label: str, i: int, priority: int) -> None:
        self.id = i
        self.label = label
        self.goals = set()
        self.priority = priority
        self.current_cell = NONE
        self.states = SimpleQueue()
        self.queued_cells = SimpleQueue()
        self.visited_cells_positions = set()

    def behave(self, state: Option[States]) -> Result[States, str]:
        # Check if the current cell is a goal, stop and return success if so.
        # if the state param is passed, continue to a state check to decide if
        # the navigator should continue the path finding
        if self.current_cell.is_some:
            if self.current_cell.unwrap().position in self.goals:
                return Ok(States.REACHED_GOAL)
        else:
            # Critical failure, it should at least always have a starting cell
            return Err("No Current Cell for nav: " + str(self.id))

        print("AAAAA: ")
        print(self.current_cell.unwrap().list_connections())

        # Check same level cells
        for cell in self.current_cell.unwrap().connections.values():
            if cell.position in self.goals:
                return Ok(States.REACHED_GOAL)
            self.queued_cells.push(cell)

        # Avoids going back to a previous visited cell
        directions_filtered: dict[Direction, Cell] = dict()
        for drt, cell in self.current_cell.unwrap().connections.items():
            directions_filtered[drt] = cell
            # if cell.position in self.visited_cells_positions:

        # Random choice for the next move
        print("CUR POS: " + str(self.current_cell.unwrap().position))
        directions = list(directions_filtered.keys())
        choice = Direction.RIGHT

        res = self.move_to_same_level_cell(choice)
        if not res:
            return Err("Failed to move to the cell")

        if self.current_cell.unwrap().position in self.goals:
            return Ok(States.REACHED_GOAL)

        return Ok(States.MOVING)

    def empty_current_cell(self) -> None:
        self.current_cell = NONE

    def get_next_same_level_cells(self) -> Option[list[Direction]]:
        if self.current_cell.is_none:
            return NONE

        return Some(list(self.current_cell.unwrap().connections.keys()))

    def move_to_same_level_cell(self, direction: Direction) -> bool:
        if self.current_cell.is_none:
            print("Curr cell is none")
            return False

        mv_cell = self.current_cell.unwrap().connections.get(direction)
        if mv_cell is None:
            print("mv_cell is none")
            return False

        moved_to_cell = self.current_cell.unwrap().get_next(direction)
        if moved_to_cell is None:
            # or moved_to_cell.unwrap().position in self.visited_cells:
            return False

        pushed = moved_to_cell.push_navigator(self)
        if not pushed:
            return False

        self.visited_cells_positions.add(self.current_cell.unwrap().position)
        return True

    def set_current_cell(self, hold: Cell) -> None:
        self.current_cell = Some(hold)

    def state_sequence(self) -> list[States]:
        return self.states.elements()

    def consume_next_state(self) -> States:
        return self.states.pop()

    def next_state(self) -> States:
        return self.states.peek()

    def add_state(self, state: States):
        self.states.push(state)

    def add_states(self, states: list[States]):
        self.states += states


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

    def attribute_starting_point_to_navigators(self, starting_points: list[Cell]):
        len_of_points = len(starting_points)

        # get a starting point list
        # make sure the list is as big as the stack, if not make it so (distribute navs "equally" through points)
        # if the cell already is occupied add the nav to the queue of the starting point
        for i, navigator in enumerate(self.stack):
            navigator.set_current_cell(starting_points[i % len_of_points])
            navigator.visited_cells_positions.add(starting_points[i % len_of_points].position)

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
            res = next_nav_s.behave(state=NONE)

            # TODO handle all the interesting states after navigator behaviour
            if res.is_ok and res.unwrap() is States.REACHED_GOAL:
                self.stack.remove(next_nav_s)
            # print(next_nav_s.current_cell.unwrap().position, end=" ")
            # print(res, end=" ")
            # print(end="\n")
            time.sleep(0.7)

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

    def __hash__(self):
        return hash((
            self.position,
            self.label
        ))

    def __init__(self, label: str, position: (int, int)):
        self.label = label
        self.position = position
        self.current = NONE
        self.queue = SimpleQueue()
        self.connections = dict()

    def push_navigator(self, nav: Navigator) -> bool:
        # if nav.current_cell.is_some:
        #     print(nav.label + " ALREADY HAS HOLDING")
        #     return False

        if self.queue.len() >= 4:
            return False

        nav.set_current_cell(self)
        if self.current.is_none and self.queue.len() < 1:
            self.current = Some(nav)
            return True
        else:
            self.queue.push(nav)
            return True

    def next_navigator(self) -> Option[Navigator]:
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

    # def get_next_in_queue(self) -> Option[Navigator]:
    #     try:
    #         next_in_queue = self.queue.pop()
    #     except IndexError:
    #         self.current = NONE
    #         return NONE
    #     self.current = Some(next_in_queue)
    #     return self.current

    def add_cel(self, direction: Direction, cell: Cell):
        cell.connections[direction.get_opposite()] = self
        self.connections[direction] = cell

    def add_cel_get_next(self, direction: Direction, cell: Cell) -> Cell:
        self.add_cel(direction, cell)
        return self.connections[direction]

    def get_next(self, direction: Direction) -> Cell | None:
        if direction in self.connections.keys():
            return self.connections[direction]
        return None


class Map:
    starting_cells: list[Cell]
    goal_cels: list[Cell]
    cels = list[list[Cell]]

    def __init__(self, m: list[list[CellType]]):
        self.starting_cells = list[Cell]()
        self.goal_cels = list[Cell]()
        self.cels = list[list[Cell]]()
        self.__build_map_from_2d_array(m)

    def starts_indexes(self) -> list[(int, int)]:
        positions = []
        for row, elems in enumerate(self.cels):
            for col, elem in enumerate(elems):
                if CellType.START.to_label() in elem.label:
                    positions.append(elem.position)
        return positions

    def __build_map_from_2d_array(self, array: list[list[CellType]]):
        current_cell: Cell | None = None

        for row, elems in enumerate(array):
            self.cels.append(list[Cell]())
            for coll, _cell in enumerate(elems):
                cell_label = array[row][coll].to_label() + " " + str(row) + " " + str(coll)
                c = Cell(label=cell_label, position=(row, coll))
                self.cels[row].append(c)

        for row, elems in enumerate(self.cels):
            for coll, cell in enumerate(elems):
                if CellType.EMPTY.to_label() in cell.label:
                    continue
                # Check for cells that connect from bellow
                if row + 1 < len(self.cels) - 1:
                    cell_bellow = self.cels[row + 1][coll]
                    if CellType.EMPTY.to_label() not in cell_bellow.label:
                        # b_cell = Cell(label=cell_label, position=(row + 1, coll))
                        # b_cell.add_cel(Direction.UP, c)
                        # BAD CONNECTIONS
                        cell.add_cel(Direction.DOWN, cell_bellow)
                        # print("B", end=" ")
                if row - 1 >= 0:
                    cell_above = self.cels[row - 1][coll]
                    if CellType.EMPTY.to_label() not in cell_above.label:
                        # b_cell = Cell(label=cell_label, position=(row - 1, coll))
                        # b_cell.add_cel(Direction.DOWN, c)
                        cell.add_cel(Direction.UP, cell_above)
                        # print("T", end=" ")
                if coll + 1 <= len(self.cels) - 1:
                    cell_right = self.cels[row][coll + 1]
                    if CellType.EMPTY.to_label() not in cell_right.label:
                        # b_cell = Cell(label=cell_label, position=(row, coll + 1))
                        # b_cell.add_cel(Direction.LEFT, c)
                        cell.add_cel(Direction.RIGHT, cell_right)
                        # print("R", end="    ")
                if coll - 1 >= 0:
                    cell_left = self.cels[row][coll - 1]
                    if cell_left != CellType.EMPTY:
                        # b_cell = Cell(label=cell_label, position=(row, coll - 1))
                        # b_cell.add_cel(Direction.RIGHT, c)
                        # print("L", end=" ")
                        cell.add_cel(Direction.LEFT, cell_left)
                # print()

                if CellType.START.to_label() in cell.label:
                    self.starting_cells.append(cell)
                if CellType.GOAL.to_label() in cell.label:
                    self.goal_cels.append(cell)

                # Make the new current cell, the cell added to the right of current cell
                # if current_cell is None:
                #     current_cell = c
                # else:
                #     current_cell = current_cell.add_cel_get_next(Direction.RIGHT, c)

    @staticmethod
    def map_from_abstraction(abstraction: list[list[str]]) -> list[list[CellType]]:
        result = list[list[CellType]]()
        for i, row in enumerate(abstraction):
            print("II: " + str(i))
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
        #   #
    S # # # #
    """
    mp = [
        [CellType.START, CellType.REGULAR, CellType.REGULAR, CellType.REGULAR, CellType.GOAL, ],
        [CellType.EMPTY, CellType.EMPTY, CellType.REGULAR, CellType.EMPTY, CellType.REGULAR, ],
        [CellType.START, CellType.REGULAR, CellType.REGULAR, CellType.REGULAR, CellType.REGULAR, ],
    ]
    mp2 = [
        [CellType.START, CellType.REGULAR, CellType.REGULAR, CellType.REGULAR, CellType.REGULAR, ],
        [CellType.EMPTY, CellType.EMPTY, CellType.REGULAR, CellType.EMPTY, CellType.EMPTY, ],
        [CellType.EMPTY, CellType.EMPTY, CellType.REGULAR, CellType.EMPTY, CellType.END, ],
    ]
    cells = Map(m=mp)
    # abstract = mazes.io.read_from_file("test_1.mz", "/home/ninbo/ws/python/ai/final_project/resources").unwrap()
    # x = Map.map_from_abstraction(abstract)
    # cls = Map(m=x)
    # for cell in cls.cels:
    #     print("CELL: " + str(cell.position) + " " + cell.list_connections())

    navigator_state = SimpleQueue(
        # States.MOVE_RIGHT, States.MOVE_RIGHT, States.DONE, States.MOVE_DOWN,
        # States.MOVE_DOWN, States.MOVE_RIGHT, States.MOVE_RIGHT,
    )
    navigator_state_2 = SimpleQueue(
        # States.MOVE_RIGHT, States.MOVE_RIGHT, States.MOVE_RIGHT,
        # States.MOVE_RIGHT, States.IS_GOAL, States.DONE
    )
    nav_1 = Navigator(label="First", priority=1, i=1)
    nav_1.goals.add((0, 4))
    navs: list[Navigator] = [
        nav_1,
        # Navigator(label="Second", priority=2, i=2),
    ]
    navigator_stack = NavigatorStack(navigators=navs)
    navigator_stack.attribute_starting_point_to_navigators(starting_points=cells.starting_cells)
    navigator_stack.run_until_end()
