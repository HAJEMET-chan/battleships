from typing import Dict, Any
import numpy as np
from scipy.ndimage import label

from .config import VERTICAL_KEYS, HORIZONTAL_KEYS

def validate_battlefield(field: Dict[str, Dict[str, Any]]) -> bool:
    size = 10
    np_field = np.zeros((size, size), dtype=int)
    

    for y_idx, y_key in enumerate(VERTICAL_KEYS.values()):
        for x_idx, x_key in enumerate(HORIZONTAL_KEYS.values()):
            if x_key in field[y_key] and field[y_key][x_key].is_part_of_ship:
                np_field[y_idx, x_idx] = 1
    

    structure = np.ones((3, 3))
    labeled, num_features = label(np_field, structure)
    

    ships = []
    for ship_num in range(1, num_features + 1):
        ship_cells = np.where(labeled == ship_num)
        min_y, max_y = min(ship_cells[0]), max(ship_cells[0])
        min_x, max_x = min(ship_cells[1]), max(ship_cells[1])

        if (max_y - min_y > 0) and (max_x - min_x > 0):
            return False 
        
        length = max(max_y - min_y, max_x - min_x) + 1
        ships.append(length)
    
    expected_ships = [1, 1, 1, 1, 2, 2, 2, 3, 3, 4]
    if sorted(ships) != expected_ships:
        return False
    
    padded_field = np.pad(np_field, pad_width=1, mode='constant', constant_values=0)
    
    for ship_num in range(1, num_features + 1):
        ship_cells = np.where(labeled == ship_num)
        min_y, max_y = min(ship_cells[0]), max(ship_cells[0])
        min_x, max_x = min(ship_cells[1]), max(ship_cells[1])
        
        region = padded_field[min_y:max_y+3, min_x:max_x+3]
        if np.sum(region) > (max_y - min_y + max_x - min_x + 1):
            return False 
    
    return True