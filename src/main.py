from typing import List, Optional, Dict, Tuple

from .validating import validate_battlefield
from .config import VERTICAL_KEYS, HORIZONTAL_KEYS, START_FIELD

def list_field_to_dict(field: List[List[int]]) -> dict:
    


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

    def __init__(self, cells: list):
        self.cells = cells
        self.is_killed = False
        self.id = self._set_id()

    def _set_id(self):
        id = ''

        id += str(len(self.cells)) + '-'

        for cell in self.cells:
            id += cell.x + cell.y
        
        return id
    
    def check_killed(self):

        for cell in self.cells:
            if not cell.is_hit:
                return False
            
        self.is_killed = True
        
        self.kill()

    def kill(self):
        for cell in self.cells:
            cell.is_killed = True
    
    def get_state(self):

        if self.is_killed:
            return 'killed'
        
        return 'alive'
    
    def __str__(self):
        return self.id
    

class Cell:

    def __init__(
            self, 
            x: str, 
            y: str, 
            is_part_of_ship: bool, 
            ship: Optional[Ship] = None
        ):

        self.x = x
        self.y = y
        self.is_part_of_ship = is_part_of_ship
        self.is_hit = False
        self.is_miss = False
        self.is_killed = False
        self.ship = ship
        self.position = (x, y)
        self.can_place_ship = True
    

    def hit(self):
        if self.is_part_of_ship:
            self.is_hit = True
        else:
            self.is_miss = True
        
        if self.ship:
            self.ship.check_killed()

    def disable_placement(self):
        self.can_place_ship = False
            
    def get_state(self):
        
        if self.is_hit:
            return 'hit'
        
        if self.is_miss:
            return 'miss'
        
        if self.is_killed:
            return 'killed'
        
        if not self.can_place_ship:
            return 'occupied'
        
        return 'empty'
    
    def _set_ship(self, ship: Ship):
        self.ship = ship
    
    def __str__(self):
        return f'{self.x}{self.y}'
    
class BattleField:

    def __init__(self):
        self.field: Dict[str, Dict[str, Cell]] = list_field_to_dict(START_FIELD)
        self.ships = []

        
    def _find_ships(self) -> List[Ship]:
        visited = {}
        for y in self.field:
            visited[y] = {x: False for x in self.field[y]}
        
        ships = []
        
        for y in sorted(self.field.keys(), key=lambda k: list(VERTICAL_KEYS.values()).index(k)):
            for x in sorted(self.field[y].keys(), key=lambda k: int(k)):
                cell = self.field[y][x]
                
                if not cell.is_part_of_ship or visited[y][x]:
                    continue

                ship_cells = []
                queue = [(x, y)]
                
                while queue:
                    current_x, current_y = queue.pop(0)
                    if visited[current_y][current_x]:
                        continue
                    
                    visited[current_y][current_x] = True
                    current_cell = self.field[current_y][current_x]
                    ship_cells.append(current_cell)
                    
                    # Проверяем соседние клетки (по горизонтали и вертикали)
                    directions = self._get_neighbor_directions(current_x, current_y)
                    
                    for dx, dy in directions:
                        nx, ny = dx, dy
                        if (ny in self.field and 
                            nx in self.field[ny] and 
                            self.field[ny][nx].is_part_of_ship and 
                            not visited[ny][nx]):
                            queue.append((nx, ny))
                

                if ship_cells:
                    ship = Ship(ship_cells)
                    ships.append(ship)

                    for ship_cell in ship_cells:
                        ship_cell._set_ship(ship)
        
        self.ships = ships

    
    def _get_neighbor_directions(self, x: str, y: str) -> List[tuple]:
        directions = []
        x_num = int(x)
        y_idx = list(VERTICAL_KEYS.values()).index(y)
        
        if x_num > 1:
            directions.append((str(x_num - 1), y))

        if x_num < 10:
            directions.append((str(x_num + 1), y))
        
        if y_idx > 0:
            directions.append((x, VERTICAL_KEYS[y_idx - 1]))
        
        if y_idx < 9:
            directions.append((x, VERTICAL_KEYS[y_idx + 1]))
        
        return directions
    
    def hit(self, x: str, y: str):
        cell = self.field[y][x]
        cell.hit()
        
    def is_game_over(self):

        for ship in self.ships:
            if ship.get_state() == 'alive':
                return False
        
        return True
    
        


a = BattleField()



