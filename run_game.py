# run_game.py
import sys
import os
from typing import Dict, Tuple

from src.main import BattleField, VERTICAL_KEYS, HORIZONTAL_KEYS
from src.main import Cell # Import Cell for type hinting in print_battlefield

from src.validating import validate_battlefield

def clear_console():
    """
    Clears the console screen. Works on both Windows ('cls') and Unix-like ('clear') systems.
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def print_battlefield(field: Dict[str, Dict[str, 'Cell']], player_name: str, is_player_own_board: bool = False):
    """
    Prints the current state of a player's battlefield.
    Args:
        field: The battlefield dictionary.
        player_name: The name of the player whose board is being displayed.
        is_player_own_board: If True, shows the player's own ships. If False, hides them (for opponent's view).
    """
    print(f"\n--- {player_name}'s Board ({'Your Ships' if is_player_own_board else 'Opponent View'}) ---")
    print("   " + "  ".join(HORIZONTAL_KEYS.values()))
    print("  " + "---" * len(HORIZONTAL_KEYS))
    for y_key in sorted(VERTICAL_KEYS.values(), key=lambda k: list(VERTICAL_KEYS.values()).index(k)):
        row_str = f"{y_key} |"
        for x_key in sorted(HORIZONTAL_KEYS.values(), key=lambda k: int(k)):
            cell = field[y_key][x_key]
            if cell.is_hit:
                row_str += " X " # Hit ship part (always visible)
            elif cell.is_miss:
                row_str += " O " # Miss (always visible)
            elif is_player_own_board and cell.is_part_of_ship:
                row_str += " S " # Unhit ship part on own board
            elif not cell.can_place_ship and is_player_own_board and not cell.is_part_of_ship:
                row_str += " . " # Occupied (cannot place ship) on own board, but not a ship itself
            else:
                row_str += " ~ " # Empty water or hidden ship
        print(row_str)
    print("  " + "---" * len(HORIZONTAL_KEYS))

def get_coords_from_input(prompt: str) -> Tuple[str, str]:
    """
    Helper to get and validate coordinates from user input.
    Ensures input is in the format 'A1' or 'K10'.
    """
    while True:
        coord_str = input(prompt).strip().upper()
        if len(coord_str) < 2 or len(coord_str) > 3:
            print("Invalid format. Enter coordinates like 'A1' or 'K10'.")
            continue

        # Handle '10' as a two-character column key
        if len(coord_str) == 3 and coord_str[1:] == '10':
            y_char = coord_str[0]
            x_num = '10'
        elif len(coord_str) == 2:
            y_char = coord_str[0]
            x_num = coord_str[1]
        else:
            print("Invalid format. Enter coordinates like 'A1' or 'K10'.")
            continue

        if y_char not in VERTICAL_KEYS.values() or x_num not in HORIZONTAL_KEYS.values():
            print("Invalid coordinates. Please use A-K for rows and 1-10 for columns.")
            continue
        return x_num, y_char

def setup_ships_manually(bf: BattleField, player_name: str):
    """
    Allows manual ship placement for a given player.
    Args:
        bf: The BattleField object for the current player.
        player_name: The name of the player.
    """
    ship_sizes = {
        4: 1, # One 4-deck ship
        3: 2, # Two 3-deck ships
        2: 3, # Three 2-deck ships
        1: 4  # Four 1-deck ships
    }

    placed_ships_count = {s: 0 for s in ship_sizes.keys()}

    clear_console()
    print(f"--- {player_name}: Ship Placement ---")
    print("Enter ship coordinates. For example, for a 3-deck ship: A1 A2 A3")
    print("You need to place:")
    for size, count in sorted(ship_sizes.items(), reverse=True):
        print(f"- {count} x {size}-deck ship")

    while True:
        all_ships_placed = True
        for size, count in ship_sizes.items():
            if placed_ships_count[size] < count:
                all_ships_placed = False
                break
        
        if all_ships_placed:
            print(f"\n{player_name}: All ships placed!")
            break

        print_battlefield(bf.field, player_name, is_player_own_board=True) # Corrected parameter name
        print(f"\n{player_name}: Remaining ships to place:")
        for size, count in ship_sizes.items():
            if placed_ships_count[size] < count:
                print(f"- {size}-deck: {count - placed_ships_count[size]} left")

        try:
            coords_input_str = input(f"[{player_name}] Enter coordinates for a ship (e.g., A1 A2 A3 for a 3-deck): ").strip()
            if not coords_input_str:
                print("No coordinates entered. Please try again.")
                continue

            coords_raw = coords_input_str.split()
            coords_list = []
            for c_str in coords_raw:
                if len(c_str) < 2 or len(c_str) > 3:
                    raise ValueError("Invalid coordinate format in input (e.g., 'A1' or 'K10').")
                
                y_char = c_str[0].upper()
                x_num = c_str[1:].upper()
                
                if y_char not in VERTICAL_KEYS.values() or x_num not in HORIZONTAL_KEYS.values():
                    raise ValueError(f"Invalid coordinate value: {c_str}. Use A-K for rows and 1-10 for columns.")
                coords_list.append((x_num, y_char))
            
            current_ship_size = len(coords_list)
            if current_ship_size not in ship_sizes:
                print(f"Invalid ship size {current_ship_size}. Ships must be 1, 2, 3, or 4 cells long.")
                continue
            if placed_ships_count[current_ship_size] >= ship_sizes[current_ship_size]:
                print(f"Too many {current_ship_size}-deck ships already placed. You need {ship_sizes[current_ship_size]}.")
                continue

            # Attempt to add the ship
            bf.add_ship(coords_list)
            placed_ships_count[current_ship_size] += 1
            print(f"Successfully placed a {current_ship_size}-deck ship for {player_name}!")

        except ValueError as e:
            print(f"Error placing ship: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        
        input("\nPress Enter to continue to the next placement...")
        clear_console()


def main():
    print("Welcome to Battleship!")

    player1_field = BattleField()
    player2_field = BattleField()

    # Player 1 ship setup
    setup_ships_manually(player1_field, "Player 1")
    # After all ships are placed, validate the entire board for Player 1
    if not validate_battlefield(player1_field.field):
        print("Player 1's final battlefield configuration is invalid. Please restart the game.")
        return # Exit if the final board is invalid

    # Player 2 ship setup
    setup_ships_manually(player2_field, "Player 2")
    # After all ships are placed, validate the entire board for Player 2
    if not validate_battlefield(player2_field.field):
        print("Player 2's final battlefield configuration is invalid. Please restart the game.")
        return # Exit if the final board is invalid


    print("\n--- All ships are placed! Game Start! ---")
    input("Press Enter to begin the game...")

    current_player_idx = 0
    players = [
        {"name": "Player 1", "own_field": player1_field, "opponent_field": player2_field},
        {"name": "Player 2", "own_field": player2_field, "opponent_field": player1_field}
    ]

    while True:
        current_player = players[current_player_idx]
        opponent_player = players[1 - current_player_idx]

        clear_console()
        print(f"--- {current_player['name']}'s Turn ---")
        
        # Display current player's own board (with ships)
        print_battlefield(current_player['own_field'].field, current_player['name'], is_player_own_board=True)
        
        # Display opponent's board (without ships)
        print_battlefield(opponent_player['own_field'].field, opponent_player['name'], is_player_own_board=False)

        try:
            x, y = get_coords_from_input(f"[{current_player['name']}] Enter target coordinates (e.g., A5): ")
            opponent_player['own_field'].hit(x, y) # Current player shoots at opponent's board

            # Check if the game is over after the shot
            if opponent_player['own_field'].is_game_over():
                clear_console()
                print(f"--- Game Over ---")
                print(f"Congratulations, {current_player['name']}! You have sunk all of {opponent_player['name']}'s ships!")
                print_battlefield(current_player['own_field'].field, current_player['name'], is_player_own_board=True)
                print_battlefield(opponent_player['own_field'].field, opponent_player['name'], is_player_own_board=True) # Show opponent's sunk ships
                break # Exit game loop
            
            input("\nPress Enter to end your turn...")
            current_player_idx = 1 - current_player_idx # Switch players

        except ValueError as e:
            print(f"Error: {e}")
            input("Press Enter to try again...")
            continue
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            input("Press Enter to try again...")
            continue

if __name__ == "__main__":
    main()
