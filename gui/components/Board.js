// gui/components/Board.js
import React, { useState, useCallback } from 'react';
import CellComponent from './CellComponent';
import { VERTICAL_KEYS, HORIZONTAL_KEYS } from '../logic/GameClasses'; // Import constants
import '../styles/App.css'; // Import the CSS file

const Board = ({ battlefield, playerName, isPlayerOwnBoard, onCellClick, isPlacingShip, currentShipCoords }) => {
  const [hoveredCoords, setHoveredCoords] = useState([]);

  // Memoized function to calculate cells to highlight during ship placement hover
  const getHoveredCells = useCallback((startCell) => {
    // If not in placement mode or no initial click, return empty
    if (!isPlacingShip || !currentShipCoords.length) return [];

    const startXNum = parseInt(currentShipCoords[0].x);
    const startYIdx = VERTICAL_KEYS.indexOf(currentShipCoords[0].y);

    const endXNum = parseInt(startCell.x);
    const endYIdx = VERTICAL_KEYS.indexOf(startCell.y);

    const newHovered = [];

    // Determine if horizontal or vertical placement is intended
    const isHorizontal = startYIdx === endYIdx;
    const isVertical = startXNum === endXNum;

    if (isHorizontal) {
      const minX = Math.min(startXNum, endXNum);
      const maxX = Math.max(startXNum, endXNum);
      for (let x = minX; x <= maxX; x++) {
        newHovered.push({ x: String(x), y: startCell.y });
      }
    } else if (isVertical) {
      const minYIdx = Math.min(startYIdx, endYIdx);
      const maxYIdx = Math.max(startYIdx, endYIdx);
      for (let yIdx = minYIdx; yIdx <= maxYIdx; yIdx++) {
        newHovered.push({ x: startCell.x, y: VERTICAL_KEYS[yIdx] });
      }
    } else {
      // If neither horizontal nor vertical, only highlight the single hovered cell
      newHovered.push({ x: startCell.x, y: startCell.y });
    }
    return newHovered;
  }, [isPlacingShip, currentShipCoords]);

  // Handle mouse entering a cell during placement
  const handleMouseEnter = useCallback((cell) => {
    if (isPlacingShip) {
      if (currentShipCoords.length > 0) {
        // If first cell is already clicked, highlight potential ship path
        const newHovered = getHoveredCells(cell);
        setHoveredCoords(newHovered.map(c => `${c.y}${c.x}`));
      } else {
        // If no cells clicked yet, just highlight the current cell
        setHoveredCoords([`${cell.y}${cell.x}`]);
      }
    }
  }, [isPlacingShip, currentShipCoords, getHoveredCells]);

  // Handle mouse leaving a cell during placement
  const handleMouseLeave = useCallback(() => {
    if (isPlacingShip) {
      setHoveredCoords([]); // Clear highlights
    }
  }, [isPlacingShip]);

  return (
    <div className="board-container">
      <h3 className="board-title">{playerName}'s Board {isPlayerOwnBoard ? '(Your Ships)' : '(Opponent View)'}</h3>
      <div className="grid-container">
        {/* Horizontal Headers */}
        <div className="cell-header"></div> {/* Empty corner */}
        {HORIZONTAL_KEYS.map(x => (
          <div key={x} className="cell-header">
            {x}
          </div>
        ))}

        {/* Board Cells */}
        {VERTICAL_KEYS.map(y => (
          <React.Fragment key={y}>
            <div className="cell-header">
              {y}
            </div>
            {HORIZONTAL_KEYS.map(x => {
              const cell = battlefield.field[y][x];
              const isCellHovered = hoveredCoords.includes(`${cell.y}${cell.x}`);
              return (
                <CellComponent
                  key={`${y}${x}`}
                  cell={cell}
                  isPlayerOwnBoard={isPlayerOwnBoard}
                  onClick={onCellClick}
                  isPlacing={isPlacingShip}
                  isHovered={isCellHovered}
                  onMouseEnter={() => handleMouseEnter(cell)}
                  onMouseLeave={handleMouseLeave}
                />
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default Board;
