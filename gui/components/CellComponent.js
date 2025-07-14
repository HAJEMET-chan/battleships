// gui/components/CellComponent.js
import React from 'react';
import '../styles/App.css'; // Import the CSS file

const CellComponent = ({ cell, isPlayerOwnBoard, onClick, isPlacing, isHovered }) => {
  let stateClass = 'cell-empty'; // Default class
  let displayChar = '~';

  // Get the display state from the Cell object
  const displayState = cell.getDisplayState(isPlayerOwnBoard);

  // Determine CSS classes and display character based on cell state
  switch (displayState) {
    case 'hit':
      stateClass = 'cell-hit';
      displayChar = 'X';
      break;
    case 'miss':
      stateClass = 'cell-miss';
      displayChar = 'O';
      break;
    case 'killed':
      stateClass = 'cell-killed';
      displayChar = 'X';
      break;
    case 'ship':
      stateClass = 'cell-ship';
      displayChar = 'S';
      break;
    case 'occupied':
      stateClass = 'cell-occupied';
      displayChar = '.';
      break;
    default: // 'empty'
      stateClass = 'cell-empty';
      displayChar = '~';
      break;
  }

  // Apply hover effects during ship placement
  if (isPlacing && isHovered) {
    if (cell.canPlaceShip && !cell.isPartOfShip) {
      stateClass = 'cell-placing-valid'; // Valid placement highlight
    } else {
      stateClass = 'cell-placing-invalid'; // Invalid placement highlight
    }
  }

  return (
    <div
      className={`cell ${stateClass}`} // Apply base cell class and state-specific class
      onClick={() => onClick(cell)} // Handle click event
    >
      <span className="cell-content">{displayChar}</span>
    </div>
  );
};

export default CellComponent;
