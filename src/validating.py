# src/validating.py
from typing import Dict, Any
import numpy as np
from scipy.ndimage import label # Used for identifying connected components (ships)

from .config import VERTICAL_KEYS, HORIZONTAL_KEYS

def validate_battlefield(field: Dict[str, Dict[str, Any]]) -> bool:
    """
    Validates a battleship field according to standard rules:
    - Exactly 10 ships: one 4-deck, two 3-deck, three 2-deck, four 1-deck.
    - Ships must be straight (horizontal or vertical).
    - Ships cannot touch each other, even diagonally.
    Args:
        field: A dictionary representation of the battlefield with Cell objects.
    Returns:
        True if the battlefield is valid, False otherwise.
    """
    size = 10
    # Create a numpy array from the dictionary field for easier processing
    np_field = np.zeros((size, size), dtype=int)

    for y_idx, y_key in enumerate(VERTICAL_KEYS.values()):
        for x_idx, x_key in enumerate(HORIZONTAL_KEYS.values()):
            # Check if the key exists and if the cell is part of a ship
            if y_key in field and x_key in field[y_key] and field[y_key][x_key].is_part_of_ship:
                np_field[y_idx, x_idx] = 1

    # Use scipy.ndimage.label to find connected components (ships)
    # A 3x3 structure means it considers all 8 neighbors and the center cell for connectivity.
    # This is crucial for detecting diagonal adjacency.
    structure = np.ones((3, 3))
    labeled, num_features = label(np_field, structure) # labeled: array with ship IDs, num_features: total ships found

    ships_lengths = []
    for ship_num in range(1, num_features + 1): # Iterate through each identified ship
        ship_cells_indices = np.where(labeled == ship_num) # Get (row_indices, col_indices) for current ship
        
        # If no cells found for this ship_num, skip (shouldn't happen with valid `label` output)
        if not ship_cells_indices[0].size:
            continue

        min_y, max_y = min(ship_cells_indices[0]), max(ship_cells_indices[0])
        min_x, max_x = min(ship_cells_indices[1]), max(ship_cells_indices[1])

        # Check for diagonal ships or L-shaped ships:
        # If a ship spans multiple rows AND multiple columns, it's not straight.
        if (max_y - min_y > 0) and (max_x - min_x > 0):
            return False # Ship is not straight (e.g., diagonal or L-shaped)

        # Calculate ship length (either height or width + 1)
        length = max(max_y - min_y, max_x - min_x) + 1
        ships_lengths.append(length)

    # Validate ship count and sizes
    # Standard Battleship ships: one 4-deck, two 3-deck, three 2-deck, four 1-deck
    expected_ships = sorted([1, 1, 1, 1, 2, 2, 2, 3, 3, 4])
    if sorted(ships_lengths) != expected_ships:
        return False # Incorrect number or sizes of ships

    # Check for ships touching diagonally or too closely
    # Pad the field with zeros to simplify boundary checks for surrounding regions
    padded_field = np.pad(np_field, pad_width=1, mode='constant', constant_values=0)

    for ship_num in range(1, num_features + 1):
        ship_cells_indices = np.where(labeled == ship_num)
        
        if not ship_cells_indices[0].size:
            continue

        min_y, max_y = min(ship_cells_indices[0]), max(ship_cells_indices[0])
        min_x, max_x = min(ship_cells_indices[1]), max(ship_cells_indices[1])

        # Define the region around the ship (including 1-cell buffer on all sides)
        # Add 1 to min/max indices because of padding
        # Add 2 to max_y/max_x to get the correct slice end for a 3x3 region (min-1 to max+1)
        region = padded_field[min_y:max_y + 3, min_x:max_x + 3] # Slice includes the padded border

        # The sum of '1's in the region should only be equal to the ship's length.
        # If it's greater, it means there's another '1' (part of another ship)
        # in the surrounding 1-cell buffer, indicating ships are too close.
        # The expected sum is just the ship's length, as the padding is 0s.
        # The actual length of the ship is (max_y - min_y + 1) if vertical, or (max_x - min_x + 1) if horizontal.
        # The sum of `np_field` (original unpadded) for this ship_num should be its length.
        actual_ship_length = len(ship_cells_indices[0]) # Number of cells in the current ship

        # Sum of the region should be exactly the ship's length. If there's any other '1'
        # in the 3x3 padded box (which includes diagonal cells), it means ships are touching.
        # The `label` function with `structure=np.ones((3,3))` already ensures that
        # diagonally touching ships are considered part of the same "feature" if they are
        # contiguous in that sense. The rule "ships cannot touch each other, even diagonally"
        # means they must be separated by at least one empty cell.
        # If `label` finds two separate features that are actually touching diagonally,
        # it means the `structure` didn't merge them.
        # The simpler check is to ensure that for any ship, its 8-directional neighbors
        # (excluding itself) are all 0s in the original `np_field`.

        # Let's re-evaluate the diagonal touch check.
        # The `label` function with `structure=np.ones((3,3))` will group diagonally touching
        # cells as part of the *same* ship. If we want them to be *separate* ships but not touching,
        # then the initial `label` should use a 4-connectivity structure (e.g., `[[0,1,0],[1,1,1],[0,1,0]]`).
        # However, the problem statement implies standard battleship rules where ships are straight
        # and cannot touch *any* other ship, even diagonally.

        # The current `label` with `np.ones((3,3))` (8-connectivity) means:
        # If two ships are diagonally adjacent, `label` will merge them into one `num_feature`.
        # Then, the `(max_y - min_y > 0) and (max_x - min_x > 0)` check will catch this merged, non-straight "ship" and return False.
        # So, this effectively handles diagonal touching by invalidating the "ship shape".

        # The `np.sum(region) > (max_y - min_y + max_x - min_x + 1)` check is actually intended
        # to catch if there are *other* ship parts (from *other* ships) within the 1-cell buffer
        # around the current ship.
        # Let's refine this check:
        # The sum of `region` should be exactly `actual_ship_length`.
        # If `np.sum(region)` is greater than `actual_ship_length`, it means there are other '1's
        # in the padded region that are not part of the current ship, indicating a violation.
        if np.sum(region) != actual_ship_length:
            return False # Ships are touching or overlapping

    return True
