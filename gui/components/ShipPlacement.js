// gui/components/ShipPlacement.js
import React, { useState, useEffect } from 'react';
import Board from './Board';
import { SHIP_CONFIG, VERTICAL_KEYS } from '../logic/GameClasses'; // Import constants

const ShipPlacement = ({ player, onShipPlaced, message, setMessage }) => {
  const [currentShipCoords, setCurrentShipCoords] = useState([]);
  const [currentShipLength, setCurrentShipLength] = useState(0);
  const [placedShipsCount, setPlacedShipsCount] = useState({});
  // requiredShips is now directly SHIP_CONFIG

  // Update placedShipsCount whenever player's ships change
  useEffect(() => {
    setPlacedShipsCount(
      Object.values(player.ownField.ships).reduce((acc, ship) => {
        acc[ship.cells.length] = (acc[ship.cells.length] || 0) + 1;
        return acc;
      }, {})
    );
  }, [player.ownField.ships]);

  // Handles clicking on a cell during ship placement
  const handleCellClick = (cell) => {
    if (cell.isPartOfShip) {
      setMessage("This cell is already part of a ship.");
      return;
    }
    if (!cell.canPlaceShip) {
      setMessage("Cannot place ship here (too close to another ship).");
      return;
    }

    const newCoords = [...currentShipCoords, { x: cell.x, y: cell.y }];

    // Basic validation for straight line and contiguity during click selection
    if (newCoords.length > 1) {
      const xNums = newCoords.map(c => parseInt(c.x));
      const yIdxs = newCoords.map(c => VERTICAL_KEYS.indexOf(c.y));

      const isHorizontal = new Set(yIdxs).size === 1;
      const isVertical = new Set(xNums).size === 1;

      if (!isHorizontal && !isVertical) {
        setMessage("Ship must be placed in a straight line (horizontal or vertical).");
        setCurrentShipCoords([]); // Reset selection
        return;
      }

      // Check contiguity for the newly added segment
      const lastCoord = newCoords[newCoords.length - 1];
      const secondLastCoord = newCoords[newCoords.length - 2];
      const dx = Math.abs(parseInt(lastCoord.x) - parseInt(secondLastCoord.x));
      const dy = Math.abs(VERTICAL_KEYS.indexOf(lastCoord.y) - VERTICAL_KEYS.indexOf(secondLastCoord.y));

      if ((dx > 1 || dy > 1) || (dx === 1 && dy === 1)) { // Not contiguous or diagonal
        setMessage("Ship cells must be contiguous and not diagonal.");
        setCurrentShipCoords([]); // Reset selection
        return;
      }
    }

    setCurrentShipCoords(newCoords);
    setCurrentShipLength(newCoords.length);
    setMessage(""); // Clear any previous error messages
  };

  // Places the selected ship on the board
  const placeCurrentShip = () => {
    if (currentShipCoords.length === 0) {
      setMessage("Please select cells for your ship first.");
      return;
    }

    const shipLength = currentShipCoords.length;

    // Check if the ship length is valid and if there are remaining ships of this type
    if (!SHIP_CONFIG[shipLength] || (placedShipsCount[shipLength] || 0) >= SHIP_CONFIG[shipLength]) {
      setMessage(`You cannot place a ${shipLength}-deck ship. Check remaining ships.`);
      return;
    }

    // Sort coordinates to ensure consistent order for BattleField.addShip
    const sortedCoords = [...currentShipCoords].sort((a, b) => {
      const yCompare = VERTICAL_KEYS.indexOf(a.y) - VERTICAL_KEYS.indexOf(b.y);
      if (yCompare !== 0) return yCompare;
      return parseInt(a.x) - parseInt(b.x);
    });

    const result = player.ownField.addShip(sortedCoords); // Call game logic to add ship
    if (result.success) {
      setMessage(`Successfully placed a ${shipLength}-deck ship!`);
      setCurrentShipCoords([]); // Clear selection
      setCurrentShipLength(0);
      // Update placedShipsCount state (will trigger useEffect)
    } else {
      setMessage(result.message); // Display error from game logic
    }
  };

  // Resets the current ship selection
  const resetPlacement = () => {
    setCurrentShipCoords([]);
    setCurrentShipLength(0);
    setMessage("");
  };

  // Check if all required ships have been placed
  const allShipsPlaced = Object.keys(SHIP_CONFIG).every(
    (len) => (placedShipsCount[len] || 0) === SHIP_CONFIG[len]
  );

  return (
    <div className="flex flex-col items-center">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">{player.name}'s Turn to Place Ships</h2>
      <Board
        battlefield={player.ownField}
        playerName={player.name}
        isPlayerOwnBoard={true}
        onCellClick={handleCellClick}
        isPlacingShip={true}
        currentShipCoords={currentShipCoords}
      />
      <div className="mt-4 p-4 bg-gray-50 rounded-lg shadow-inner w-full max-w-md">
        <h3 className="text-xl font-semibold mb-2 text-gray-700">Ship Placement Status:</h3>
        <ul className="list-disc list-inside mb-4">
          {Object.entries(SHIP_CONFIG).sort((a, b) => b[0] - a[0]).map(([length, required]) => (
            <li key={length} className="text-gray-600">
              {required} x {length}-deck ship(s): <span className="font-medium">{(placedShipsCount[length] || 0)}/{required} placed</span>
            </li>
          ))}
        </ul>
        <p className="text-lg font-bold text-red-600 mb-2">{message}</p>
        <div className="flex justify-center space-x-4">
          <button
            onClick={placeCurrentShip}
            className="px-6 py-2 bg-green-600 text-white font-semibold rounded-lg shadow-md hover:bg-green-700 transition duration-200 disabled:opacity-50"
            // Disable if no cells selected, or if ship length is invalid, or if too many of this ship type are already placed
            disabled={
              currentShipLength === 0 ||
              !Object.keys(SHIP_CONFIG).includes(String(currentShipLength)) ||
              (placedShipsCount[currentShipLength] || 0) >= SHIP_CONFIG[currentShipLength]
            }
          >
            Place {currentShipLength}-deck Ship
          </button>
          <button
            onClick={resetPlacement}
            className="px-6 py-2 bg-yellow-500 text-white font-semibold rounded-lg shadow-md hover:bg-yellow-600 transition duration-200"
          >
            Reset Selection
          </button>
        </div>
        {allShipsPlaced && (
          <button
            onClick={onShipPlaced}
            className="mt-4 w-full px-6 py-3 bg-blue-600 text-white font-bold text-lg rounded-lg shadow-lg hover:bg-blue-700 transition duration-200"
          >
            Finish Placement for {player.name}
          </button>
        )}
      </div>
    </div>
  );
};

export default ShipPlacement;
