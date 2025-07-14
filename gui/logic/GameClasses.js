// gui/logic/GameClasses.js

// --- Configuration Constants (from src/config.py equivalent) ---
export const VERTICAL_KEYS = ['А', 'Б', 'В', 'Г', 'Д', 'Е', 'Ж', 'З', 'И', 'К'];
export const HORIZONTAL_KEYS = Array.from({ length: 10 }, (_, i) => String(i + 1));
export const BOARD_SIZE = 10;

export const SHIP_CONFIG = {
  4: 1, // One 4-deck ship
  3: 2, // Two 3-deck ships
  2: 3, // Three 2-deck ships
  1: 4  // Four 1-deck ships
};

// --- Core Game Logic (Simplified JavaScript Equivalent of Python Classes) ---

export class Cell {
  constructor(x, y, isPartOfShip = false, ship = null) {
    this.x = x;
    this.y = y;
    this.isPartOfShip = isPartOfShip;
    this.isHit = false;
    this.isMiss = false;
    this.isKilled = false;
    this.ship = ship; // Reference to Ship object
    this.position = `${y}${x}`; // e.g., "A1"
    this.canPlaceShip = true; // For UI placement rules (prevents ships from touching)
  }

  // Processes a hit on this cell
  hit() {
    if (this.isHit || this.isMiss) {
      return { success: false, message: "Cell already targeted." };
    }

    if (this.isPartOfShip) {
      this.isHit = true;
      if (this.ship) {
        this.ship.checkKilled(); // Check if the ship is now sunk
        if (this.ship.isKilled) {
          return { success: true, message: `Hit! Ship ${this.ship.id} sunk!`, shipSunk: true };
        }
      }
      return { success: true, message: "Hit!", shipSunk: false };
    } else {
      this.isMiss = true;
      return { success: true, message: "Miss.", shipSunk: false };
    }
  }

  // Determines the display state of the cell for the UI
  getDisplayState(isPlayerOwnBoard = false) {
    if (this.isHit) return 'hit'; // Red 'X' for a hit cell
    if (this.isMiss) return 'miss'; // Gray 'O' for a missed shot
    if (this.isKilled) return 'killed'; // Dark Red 'X' for a cell part of a sunk ship
    if (isPlayerOwnBoard && this.isPartOfShip) return 'ship'; // Blue 'S' for an unhit ship part on own board
    if (isPlayerOwnBoard && !this.canPlaceShip) return 'occupied'; // Light gray '.' for a zone where ships cannot be placed
    return 'empty'; // Water '~'
  }

  // Disables placement on this cell (used for areas around placed ships)
  disablePlacement() {
    this.canPlaceShip = false;
  }
}

export class Ship {
  constructor(cells) {
    this.cells = cells; // Array of Cell objects
    this.isKilled = false;
    this.id = this._setId(); // Unique ID for the ship
  }

  // Generates a unique ID for the ship based on its length and cell positions
  _setId() {
    let id = `${this.cells.length}-`;
    for (const cell of this.cells) {
      id += cell.position;
    }
    return id;
  }

  // Checks if all cells of the ship have been hit
  checkKilled() {
    this.isKilled = this.cells.every(cell => cell.isHit);
    if (this.isKilled) {
      this.kill(); // If killed, mark all its cells as killed
    }
  }

  // Marks all cells belonging to this ship as 'killed'
  kill() {
    for (const cell of this.cells) {
      cell.isKilled = true;
    }
  }

  // Returns true if the ship is still alive
  isAlive() {
    return !this.isKilled;
  }
}

export class BattleField {
  constructor() {
    this.field = this._initializeField(); // 2D dictionary of Cell objects
    this.ships = []; // Array of Ship objects
  }

  // Initializes the 10x10 field with empty Cell objects
  _initializeField() {
    const field = {};
    VERTICAL_KEYS.forEach(y => {
      field[y] = {};
      HORIZONTAL_KEYS.forEach(x => {
        field[y][x] = new Cell(x, y);
      });
    });
    return field;
  }

  // Helper to get neighbor coordinates (including diagonals for placement check)
  _getNeighborCoords(x, y) {
    const neighbors = [];
    const xNum = parseInt(x);
    const yIdx = VERTICAL_KEYS.indexOf(y);

    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (dx === 0 && dy === 0) continue; // Skip self (the cell itself)

        const nyIdx = yIdx + dy;
        const nxNum = xNum + dx;

        // Check if neighbor coordinates are within board bounds
        if (nyIdx >= 0 && nyIdx < BOARD_SIZE && nxNum >= 1 && nxNum <= BOARD_SIZE) {
          neighbors.push({ x: String(nxNum), y: VERTICAL_KEYS[nyIdx] });
        }
      }
    }
    return neighbors;
  }

  // Validates if a new ship can be placed at the given coordinates
  _isValidNewShipPlacement(coords) {
    if (!coords || coords.length === 0) {
      throw new Error("Ship coordinates cannot be empty.");
    }

    // Check each proposed cell for validity
    for (const { x, y } of coords) {
      if (!this.field[y] || !this.field[y][x]) {
        throw new Error(`Coordinate (${x}, ${y}) is out of bounds.`);
      }
      const cell = this.field[y][x];
      if (cell.isPartOfShip) {
        throw new Error(`Ship overlaps with an existing ship at ${x}${y}.`);
      }
      if (!cell.canPlaceShip) {
        throw new Error(`Cannot place ship at ${x}${y} due to proximity to another ship.`);
      }
    }

    // Check for straightness and contiguity for multi-cell ships
    if (coords.length > 1) {
      const xNums = coords.map(c => parseInt(c.x));
      const yIdxs = coords.map(c => VERTICAL_KEYS.indexOf(c.y));

      const isHorizontal = new Set(yIdxs).size === 1; // All y-indices are the same
      const isVertical = new Set(xNums).size === 1;   // All x-numbers are the same

      if (!isHorizontal && !isVertical) {
        throw new Error("Ship must be placed in a straight line (horizontal or vertical).");
      }

      // Check contiguity (cells must be consecutive)
      if (isHorizontal) {
        const sortedX = [...xNums].sort((a, b) => a - b);
        for (let i = 1; i < sortedX.length; i++) {
          if (sortedX[i] !== sortedX[i - 1] + 1) {
            throw new Error("Horizontal ship cells are not contiguous.");
          }
        }
      } else { // isVertical
        const sortedY = [...yIdxs].sort((a, b) => a - b);
        for (let i = 1; i < sortedY.length; i++) {
          if (sortedY[i] !== sortedY[i - 1] + 1) {
            throw new Error("Vertical ship cells are not contiguous.");
          }
        }
      }
    }
    return true;
  }

  // Adds a ship to the battlefield
  addShip(coords) {
    try {
      this._isValidNewShipPlacement(coords); // Validate placement first

      const newShipCells = coords.map(({ x, y }) => this.field[y][x]);
      const newShip = new Ship(newShipCells);

      // Mark cells as part of the new ship and link them to the Ship object
      newShipCells.forEach(cell => {
        cell.isPartOfShip = true;
        cell.ship = newShip;
      });

      this.ships.push(newShip); // Add new ship to the list of ships
      this._disableSurroundingCellsForShip(newShipCells); // Disable placement in surrounding cells
      return { success: true, message: "Ship placed successfully." };
    } catch (error) {
      return { success: false, message: `Error placing ship: ${error.message}` };
    }
  }

  // Disables ship placement in cells surrounding the given ship (including the ship's own cells)
  _disableSurroundingCellsForShip(shipCells) {
    shipCells.forEach(cell => {
      const neighbors = this._getNeighborCoords(cell.x, cell.y);
      // Disable the ship's own cell for placement (prevents placing another ship on top)
      this.field[cell.y][cell.x].disablePlacement();

      // Disable placement for all 8 neighbors if they are not already part of a ship
      neighbors.forEach(nCoord => {
        const neighborCell = this.field[nCoord.y]?.[nCoord.x];
        if (neighborCell && !neighborCell.isPartOfShip) {
          neighborCell.disablePlacement();
        }
      });
    });
  }

  // Checks if the game is over (all ships are sunk)
  isGameOver() {
    return this.ships.every(ship => !ship.isAlive());
  }
}
