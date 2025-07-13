from typing import List, Tuple
from collections import defaultdict

def validate_battlefield(field: List[List[int]]) -> bool:
    if len(field) != 10 or any(len(row) != 10 for row in field):
        return False

    ships_count = defaultdict(int)
    visited = [[False for _ in range(10)] for _ in range(10)]
    
    for i in range(10):
        for j in range(10):
            if field[i][j] == 1 and not visited[i][j]:
                
                size, is_horizontal = _check_ship(field, i, j, visited)
                if size == 0 or size > 4:
                    return False
                
                if not _validate_ship_shape(field, i, j, size, is_horizontal):
                    return False
                
                if not _validate_ship_environment(field, i, j, size, is_horizontal):
                    return False
                
                ships_count[size] += 1

    required_ships = {1: 4, 2: 3, 3: 2, 4: 1}
    if ships_count != required_ships:
        return False

    return True

def _check_ship(field: List[List[int]], i: int, j: int, visited: List[List[bool]]) -> Tuple[int, bool]:
    size = 1
    visited[i][j] = True
    

    horizontal = True
    k = j + 1
    while k < 10 and field[i][k] == 1:
        if visited[i][k]:
            return (0, False)  
        visited[i][k] = True
        size += 1
        k += 1
    

    if size == 1:
        horizontal = False
        k = i + 1
        while k < 10 and field[k][j] == 1:
            if visited[k][j]:
                return (0, False)
            visited[k][j] = True
            size += 1
            k += 1
    
    return (size, horizontal)

def _validate_ship_shape(field: List[List[int]], i: int, j: int, size: int, is_horizontal: bool) -> bool:

    if is_horizontal:

        for x in range(j, j + size):

            if i > 0 and field[i-1][x] == 1:
                return False

            if i < 9 and field[i+1][x] == 1:
                return False
    else:

        for y in range(i, i + size):

            if j > 0 and field[y][j-1] == 1:
                return False

            if j < 9 and field[y][j+1] == 1:
                return False
    return True

def _validate_ship_environment(field: List[List[int]], i: int, j: int, size: int, is_horizontal: bool) -> bool:
    if is_horizontal:
        min_row = max(0, i - 1)
        max_row = min(9, i + 1)
        min_col = max(0, j - 1)
        max_col = min(9, j + size)
    else:
        min_row = max(0, i - 1)
        max_row = min(9, i + size)
        min_col = max(0, j - 1)
        max_col = min(9, j + 1)
    
    for y in range(min_row, max_row + 1):
        for x in range(min_col, max_col + 1):
            # Пропускаем сам корабль
            if (is_horizontal and y == i and j <= x < j + size) or \
               (not is_horizontal and x == j and i <= y < i + size):
                continue
            if field[y][x] == 1:
                return False
    return True