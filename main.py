from typing import List, Optional, Dict, Tuple



VERTICAL_KEYS = {
    0: 'А',
    1: 'Б',
    2: 'В',
    3: 'Г',
    4: 'Д',
    5: 'Е',
    6: 'Ж',
    7: 'З',
    8: 'И',
    9: 'К'
}

HORIZONTAL_KEYS = {
    0: '1',
    1: '2',
    2: '3',
    3: '4',
    4: '5',
    5: '6',
    6: '7',
    7: '8',
    8: '9',
    9: '10'
}

battleField = [[1, 0, 0, 0, 0, 1, 1, 0, 0, 0],
                [1, 0, 1, 0, 0, 0, 0, 0, 1, 0],
                [1, 0, 1, 0, 1, 1, 1, 0, 1, 0],
                [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 1, 1, 1, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
                [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
                [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]


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

    def hit(self):
        if self.is_part_of_ship:
            self.is_hit = True
        else:
            self.is_miss = True
        
        if self.ship:
            pass
            
    def get_state(self):
        
        if self.is_hit:
            return 'hit'
        
        if self.is_miss:
            return 'miss'
        
        if self.is_killed:
            return 'killed'
        
        return 'empty'
    
    def _set_ship(self, ship: Ship):
        self.ship = ship
    
    def __str__(self):
        return f'{self.x}{self.y}'
    
class BattleField:

    def __init__(self, field: List[List[int]]):
        self.field: Dict[str, Dict[str, Cell]] = list_field_to_dict(field)
        self.ships = []
        self._find_ships()
        
    def _find_ships(self):
        visited = set()
        ships = []

        for y in self.field:
            for x in self.field[y]:
                cell = self.field[y][x]
                
                if not cell.is_part_of_ship or (x, y) in visited:
                    continue
                
                ship_cells = []
                queue = [(x, y)]
                
                while queue:
                    current_x, current_y = queue.pop(0)
                    if (current_x, current_y) in visited:
                        continue
                    
                    visited.add((current_x, current_y))
                    current_cell = self.field[current_y][current_x]
                    ship_cells.append(current_cell)

                    if current_x != '1':
                        left_x = str(int(current_x) - 1)
                        if left_x in self.field[current_y] and self.field[current_y][left_x].is_part_of_ship:
                            queue.append((left_x, current_y))
                    
                    if current_x != '10':
                        right_x = str(int(current_x) + 1)
                        if right_x in self.field[current_y] and self.field[current_y][right_x].is_part_of_ship:
                            queue.append((right_x, current_y))
                    
                    current_vertical_idx = [k for k, v in VERTICAL_KEYS.items() if v == current_y][0]
                    if current_vertical_idx > 0:
                        up_y = VERTICAL_KEYS[current_vertical_idx - 1]
                        if current_x in self.field[up_y] and self.field[up_y][current_x].is_part_of_ship:
                            queue.append((current_x, up_y))
                    
                    if current_vertical_idx < 9:
                        down_y = VERTICAL_KEYS[current_vertical_idx + 1]
                        if current_x in self.field[down_y] and self.field[down_y][current_x].is_part_of_ship:
                            queue.append((current_x, down_y))
                
                if ship_cells:
                    ship = Ship(ship_cells)
                    ships.append(ship)

                    for ship_cell in ship_cells:
                        ship_cell._set_ship(ship)
        
        self.ships = ships

a = BattleField(battleField)



