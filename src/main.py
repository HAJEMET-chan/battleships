# src/main.py
from typing import List, Optional, Dict, Tuple
import copy # Import copy for deep copying the field

from .validating import validate_battlefield
from .config import VERTICAL_KEYS, HORIZONTAL_KEYS, START_FIELD

def list_field_to_dict(field: List[List[int]]) -> Dict[str, Dict[str, 'Cell']]:
    """
    Converts a 2D list representation of the battlefield into a dictionary
    of dictionaries, where keys are coordinate strings (e.g., 'A', '1')
    and values are Cell objects.
    """
    field_dict = {}

    for row_index, row in enumerate(field):
        field_dict[VERTICAL_KEYS[row_index]] = {}

        for col_index, col in enumerate(row):
            cell = Cell(
                x=HORIZONTAL_KEYS[col_index],
                y=VERTICAL_KEYS[row_index],
                is_part_of_ship=bool(col)
            )
            field_dict[VERTICAL_KEYS[row_index]][HORIZONTAL_KEYS[col_index]] = cell

    return field_dict


class Ship:
    """Represents a single ship on the battlefield."""

    def __init__(self, cells: List['Cell']):
        """
        Initializes a Ship object.
        Args:
            cells: A list of Cell objects that constitute this ship.
        """
        self.cells = cells
        self.is_killed = False
        self.id = self._set_id() # Unique ID for the ship

    def _set_id(self) -> str:
        """Generates a unique ID for the ship based on its length and cell coordinates."""
        ship_id = str(len(self.cells)) + '-'
        for cell in self.cells:
            ship_id += cell.x + cell.y
        return ship_id

    def check_killed(self):
        """
        Checks if all cells of the ship have been hit.
        If so, marks the ship as killed and updates its cells.
        """
        for cell in self.cells:
            if not cell.is_hit:
                self.is_killed = False # Ensure it's false if not all hit
                return

        self.is_killed = True
        self.kill() # Mark all cells as killed

    def kill(self):
        """Marks all cells belonging to this ship as 'killed'."""
        for cell in self.cells:
            cell.is_killed = True

    def get_state(self) -> str:
        """Returns the current state of the ship ('killed' or 'alive')."""
        if self.is_killed:
            return 'killed'
        return 'alive'

    def __str__(self) -> str:
        """String representation of the ship (its ID)."""
        return self.id


class Cell:
    """Represents a single cell on the battlefield."""

    def __init__(
            self,
            x: str,
            y: str,
            is_part_of_ship: bool,
            ship: Optional[Ship] = None
    ):
        """
        Initializes a Cell object.
        Args:
            x: The horizontal coordinate (e.g., '1', '2').
            y: The vertical coordinate (e.g., 'A', 'Б').
            is_part_of_ship: True if this cell is part of a ship, False otherwise.
            ship: The Ship object this cell belongs to, if any.
        """
        self.x = x
        self.y = y
        self.is_part_of_ship = is_part_of_ship
        self.is_hit = False  # True if this cell has been hit by a shot
        self.is_miss = False # True if a shot landed here but it was empty
        self.is_killed = False # True if this cell's ship has been killed
        self.ship = ship     # Reference to the Ship object it belongs to
        self.position = (x, y)
        self.can_place_ship = True # True if a new ship can be placed here or adjacent

    def hit(self):
        """
        Marks the cell as hit or miss based on whether it's part of a ship.
        If it's part of a ship, it also checks if the ship is killed.
        """
        if self.is_part_of_ship:
            self.is_hit = True
            if self.ship: # If this cell is part of a ship, check its status
                self.ship.check_killed()
        else:
            self.is_miss = True

    def disable_placement(self):
        """Disables ship placement on this cell, used for areas around existing ships."""
        self.can_place_ship = False

    def get_state(self) -> str:
        """Returns the current visual state of the cell."""
        if self.is_hit:
            return 'hit' # A ship part was hit
        if self.is_miss:
            return 'miss' # An empty cell was shot
        if self.is_killed:
            return 'killed' # A ship part that belongs to a killed ship
        if not self.can_place_ship and self.is_part_of_ship:
            return 'ship' # A part of an un-hit, un-killed ship
        if not self.can_place_ship:
            return 'occupied' # Area around a ship where new ships can't be placed
        return 'empty' # Default empty cell

    def _set_ship(self, ship: Ship):
        """Internal method to associate this cell with a Ship object."""
        self.ship = ship

    def __str__(self) -> str:
        """String representation of the cell (its coordinates)."""
        return f'{self.x}{self.y}'


class BattleField:
    """Manages the game board, including cells and ships."""

    def __init__(self):
        """Initializes the battlefield with empty cells and no ships."""
        self.field: Dict[str, Dict[str, Cell]] = list_field_to_dict(START_FIELD)
        self.ships: List[Ship] = []

    def _add_ship_to_field_data(self, field_data: Dict[str, Dict[str, Cell]], coords: List[Tuple[str, str]]):
        """
        Helper to mark cells as part of a ship in a given field dictionary.
        Used for both temporary validation and final application.
        """
        for x, y in coords:
            if y in field_data and x in field_data[y]:
                field_data[y][x].is_part_of_ship = True
            else:
                # This should ideally not happen if coords are within valid bounds
                raise ValueError(f"Coordinate ({x}, {y}) is out of bounds for ship placement.")

    def _disable_surrounding_cells_for_ship(self, ship_cells: List[Cell]):
        """
        Disables ship placement for cells surrounding a given ship (including the ship's own cells).
        This ensures ships are not placed too close to each other.
        """
        for cell in ship_cells:
            x_num = int(cell.x)
            y_idx = list(VERTICAL_KEYS.values()).index(cell.y)

            # Iterate through a 3x3 grid around each ship cell (including the cell itself)
            for dy_offset in [-1, 0, 1]:
                for dx_offset in [-1, 0, 1]:
                    ny_idx = y_idx + dy_offset
                    nx_num = x_num + dx_offset

                    # Check boundaries for the 10x10 grid (1-10 for x, 0-9 for y_idx)
                    if 0 <= ny_idx < len(VERTICAL_KEYS) and 1 <= nx_num <= len(HORIZONTAL_KEYS):
                        nx = HORIZONTAL_KEYS[nx_num - 1] # Convert back to string key (e.g., 1 -> '1', 10 -> '10')
                        ny = VERTICAL_KEYS[ny_idx]

                        # Ensure the cell exists in the field and disable placement
                        if ny in self.field and nx in self.field[ny]:
                            self.field[ny][nx].disable_placement()

    def _is_valid_new_ship_placement(self, coords: List[Tuple[str, str]]) -> bool:
        """
        Checks if the proposed new ship placement is valid:
        - All cells are within bounds.
        - No cells are already part of a ship.
        - All cells allow ship placement (can_place_ship is True).
        - The ship is straight (horizontal or vertical).
        - The ship's cells are contiguous.
        """
        if not coords:
            raise ValueError("Ship coordinates cannot be empty.")

        # Check if all cells are within bounds, not overlapping, and allow placement
        for x, y in coords:
            if y not in self.field or x not in self.field[y]:
                raise ValueError(f"Coordinate ({x}, {y}) is out of bounds.")
            cell = self.field[y][x]
            if cell.is_part_of_ship:
                raise ValueError(f"Ship overlaps with an existing ship at {x}{y}.")
            if not cell.can_place_ship:
                raise ValueError(f"Cannot place ship at {x}{y} due to proximity to another ship.")

        # Check for straightness and contiguity
        if len(coords) == 1: # Single-cell ship is always valid
            return True

        # Convert string coordinates to numeric for easier comparison
        num_coords = []
        for x, y in coords:
            x_num = int(x)
            y_idx = list(VERTICAL_KEYS.values()).index(y)
            num_coords.append((x_num, y_idx))

        # Sort coordinates to simplify contiguity check
        num_coords.sort()

        is_horizontal = all(c[1] == num_coords[0][1] for c in num_coords) # All y_idx are the same
        is_vertical = all(c[0] == num_coords[0][0] for c in num_coords)   # All x_num are the same

        if not (is_horizontal or is_vertical):
            raise ValueError("Ship must be placed in a straight line (horizontal or vertical).")

        # Check contiguity
        if is_horizontal:
            # Check if x-coordinates are consecutive
            for i in range(1, len(num_coords)):
                if num_coords[i][0] != num_coords[i-1][0] + 1:
                    raise ValueError("Horizontal ship cells are not contiguous.")
        elif is_vertical:
            # Check if y-indices are consecutive
            for i in range(1, len(num_coords)):
                if num_coords[i][1] != num_coords[i-1][1] + 1:
                    raise ValueError("Vertical ship cells are not contiguous.")

        return True


    def add_ship(self, coords: List[Tuple[str, str]]):
        """
        Adds a ship to the battlefield after validating its placement.
        This validation ensures the ship is placed correctly and doesn't violate
        local Battleship rules (e.g., overlapping, too close, invalid shape/size).
        The overall board validation (correct number/types of ships) is done separately.
        Args:
            coords: A list of (x, y) tuples representing the coordinates of the ship's cells.
        Raises:
            ValueError: If the placement is invalid.
        """
        # Validate the proposed new ship placement locally
        # This will raise ValueError if any local rule is violated
        self._is_valid_new_ship_placement(coords)

        # If local validation passes, apply changes to the actual field
        self._add_ship_to_field_data(self.field, coords)

        # Re-find all ships on the updated actual field.
        # This step is crucial as it creates new Ship objects and associates them with cells.
        self._find_ships()

        # After _find_ships, the cells in 'coords' now correctly reference their new Ship object.
        # We can now disable placement for the surrounding cells based on the new ship's location.
        new_ship_cells = [self.field[y][x] for x, y in coords]
        self._disable_surrounding_cells_for_ship(new_ship_cells)


    def _find_ships(self) -> None:
        """
        Identifies all ships on the battlefield using a Breadth-First Search (BFS) approach.
        Updates the self.ships list and associates cells with their respective Ship objects.
        """
        visited = {}
        for y_key in self.field:
            visited[y_key] = {x_key: False for x_key in self.field[y_key]}

        ships_found: List[Ship] = []

        # Iterate through the field systematically
        # Sort keys to ensure consistent ship finding order (e.g., 'A' before 'Б', '1' before '2')
        sorted_y_keys = sorted(self.field.keys(), key=lambda k: list(VERTICAL_KEYS.values()).index(k))
        for y in sorted_y_keys:
            sorted_x_keys = sorted(self.field[y].keys(), key=lambda k: int(k))
            for x in sorted_x_keys:
                cell = self.field[y][x]

                # If it's not a ship part or already visited, skip
                if not cell.is_part_of_ship or visited[y][x]:
                    continue

                ship_cells: List[Cell] = []
                queue: List[Tuple[str, str]] = [(x, y)]

                while queue:
                    current_x, current_y = queue.pop(0)

                    # If already visited in this BFS, skip
                    if visited[current_y][current_x]:
                        continue

                    visited[current_y][current_x] = True
                    current_cell = self.field[current_y][current_x]
                    ship_cells.append(current_cell)

                    # Check neighboring cells (horizontal and vertical only for ship continuity)
                    # The `_get_neighbor_directions` returns (nx, ny) tuples
                    neighbor_coords = self._get_neighbor_directions(current_x, current_y)

                    for nx, ny in neighbor_coords:
                        if (ny in self.field and
                            nx in self.field[ny] and
                            self.field[ny][nx].is_part_of_ship and
                            not visited[ny][nx]):
                            queue.append((nx, ny))

                if ship_cells:
                    ship = Ship(ship_cells)
                    ships_found.append(ship)
                    # Associate each cell with the newly found ship
                    for ship_cell in ship_cells:
                        ship_cell._set_ship(ship)

        self.ships = ships_found

    def _get_neighbor_directions(self, x: str, y: str) -> List[Tuple[str, str]]:
        """
        Returns a list of valid horizontal and vertical neighbor coordinates for a given cell.
        Used internally by _find_ships to determine ship continuity.
        """
        directions = []
        x_num = int(x)
        y_idx = list(VERTICAL_KEYS.values()).index(y)

        # Check left
        if x_num > 1:
            directions.append((str(x_num - 1), y))
        # Check right
        if x_num < 10:
            directions.append((str(x_num + 1), y))
        # Check up
        if y_idx > 0:
            directions.append((x, VERTICAL_KEYS[y_idx - 1]))
        # Check down
        if y_idx < 9:
            directions.append((x, VERTICAL_KEYS[y_idx + 1]))

        return directions

    def hit(self, x: str, y: str):
        """
        Processes a shot at the given coordinates.
        Args:
            x: Horizontal coordinate.
            y: Vertical coordinate.
        Raises:
            ValueError: If coordinates are out of bounds or already hit/missed.
        """
        if y not in self.field or x not in self.field[y]:
            raise ValueError(f"Coordinates ({x}, {y}) are out of bounds.")

        cell = self.field[y][x]
        if cell.is_hit or cell.is_miss:
            print(f"Cell {x}{y} has already been targeted. Try again.")
            return

        cell.hit()
        if cell.is_hit:
            print(f"Hit at {x}{y}!")
            if cell.ship and cell.ship.is_killed:
                print(f"Ship {cell.ship.id} sunk!")
        else:
            print(f"Miss at {x}{y}.")

    def is_game_over(self) -> bool:
        """Checks if all ships on the battlefield have been sunk."""
        for ship in self.ships:
            if ship.get_state() == 'alive':
                return False
        return True
