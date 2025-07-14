# src/api.py
from typing import List, Dict, Tuple, Any, Optional

# Import core game logic components
from .main import BattleField, Cell, VERTICAL_KEYS, HORIZONTAL_KEYS
from .validating import validate_battlefield as validate_full_battlefield_core

def create_new_game() -> BattleField:
    """
    Initializes and returns a new BattleField instance.
    """
    return BattleField()

def place_ship(battlefield: BattleField, coords: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    Attempts to place a ship on the given battlefield.

    Args:
        battlefield: The BattleField instance to place the ship on.
        coords: A list of (x, y) tuples representing the coordinates of the ship's cells.

    Returns:
        A dictionary indicating success and a message.
        Example: {"success": True, "message": "Ship placed successfully."}
                 {"success": False, "message": "Error: Invalid ship placement."}
    """
    try:
        battlefield.add_ship(coords)
        return {"success": True, "message": "Ship placed successfully."}
    except ValueError as e:
        return {"success": False, "message": f"Error: {e}"}
    except Exception as e:
        return {"success": False, "message": f"An unexpected error occurred: {e}"}

def make_shot(battlefield: BattleField, x: str, y: str) -> Dict[str, Any]:
    """
    Processes a shot at the specified coordinates on the battlefield.

    Args:
        battlefield: The BattleField instance to shoot at.
        x: The horizontal coordinate (e.g., '1', '10').
        y: The vertical coordinate (e.g., 'A', 'К').

    Returns:
        A dictionary containing the result of the shot:
        - "success": True if the shot was valid, False otherwise.
        - "message": A descriptive message about the shot.
        - "cell_state": The state of the targeted cell ("hit", "miss", "killed", "already_shot").
        - "ship_sunk_id": The ID of the ship if it was sunk by this shot, otherwise None.
        - "game_over": True if the game is over after this shot, False otherwise.
    """
    if y not in battlefield.field or x not in battlefield.field[y]:
        return {"success": False, "message": f"Coordinates ({x}, {y}) are out of bounds.", "cell_state": None, "ship_sunk_id": None, "game_over": False}

    cell = battlefield.field[y][x]
    if cell.is_hit or cell.is_miss:
        return {"success": False, "message": f"Cell {x}{y} has already been targeted. Try again.", "cell_state": "already_shot", "ship_sunk_id": None, "game_over": False}

    try:
        battlefield.hit(x, y)
        cell_state = cell.get_state()
        ship_sunk_id = None
        if cell_state == 'hit' and cell.ship and cell.ship.is_killed:
            ship_sunk_id = cell.ship.id
            message = f"Hit at {x}{y}! Ship {ship_sunk_id} sunk!"
        elif cell_state == 'hit':
            message = f"Hit at {x}{y}!"
        else: # cell_state == 'miss'
            message = f"Miss at {x}{y}."

        game_over = battlefield.is_game_over()

        return {
            "success": True,
            "message": message,
            "cell_state": cell_state,
            "ship_sunk_id": ship_sunk_id,
            "game_over": game_over
        }
    except Exception as e:
        return {"success": False, "message": f"An unexpected error occurred during shot: {e}", "cell_state": None, "ship_sunk_id": None, "game_over": False}

def get_board_state(battlefield: BattleField, show_ships: bool = False) -> List[List[str]]:
    """
    Returns a 2D list representation of the battlefield's current state.

    Args:
        battlefield: The BattleField instance.
        show_ships: If True, ship locations are revealed. If False, they are hidden.

    Returns:
        A 2D list of strings, where each string represents the state of a cell:
        "X" (hit), "O" (miss), "S" (ship, if show_ships=True), "." (occupied/no placement), "~" (empty).
    """
    board_state = []
    for y_key in sorted(VERTICAL_KEYS.values(), key=lambda k: list(VERTICAL_KEYS.values()).index(k)):
        row_state = []
        for x_key in sorted(HORIZONTAL_KEYS.values(), key=lambda k: int(k)):
            cell = battlefield.field[y_key][x_key]
            if cell.is_hit:
                row_state.append("X") # Hit ship part
            elif cell.is_miss:
                row_state.append("O") # Missed shot
            elif show_ships and cell.is_part_of_ship:
                row_state.append("S") # Unhit ship part on own board
            elif show_ships and not cell.can_place_ship and not cell.is_part_of_ship:
                row_state.append(".") # Occupied (cannot place ship) on own board, but not a ship itself
            else:
                row_state.append("~") # Empty water or hidden ship
        board_state.append(row_state)
    return board_state

def is_game_finished(battlefield: BattleField) -> bool:
    """
    Checks if all ships on the battlefield have been sunk.
    """
    return battlefield.is_game_over()

def validate_full_battlefield(battlefield: BattleField) -> Dict[str, Any]:
    """
    Validates the entire battlefield configuration (all ships placed correctly).
    This function should be called after all ships have been placed.

    Args:
        battlefield: The BattleField instance to validate.

    Returns:
        A dictionary with "is_valid": True/False and a "message".
    """
    is_valid = validate_full_battlefield_core(battlefield.field)
    if is_valid:
        return {"is_valid": True, "message": "Battlefield is valid."}
    else:
        return {"is_valid": False, "message": "Battlefield configuration is invalid. Check ship count, sizes, shapes, and spacing."}

