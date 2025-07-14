// gui/components/CellComponent.js
import React from 'react';

const CellComponent = ({ cell, isPlayerOwnBoard, onClick, isPlacing, isHovered }) => {
  let stateClass = '';
  let displayChar = '';

  // Get the display state from the Cell object
  const displayState = cell.getDisplayState(isPlayerOwnBoard);

  // Determine CSS classes and display character based on cell state
  switch (displayState) {
    case 'hit':
      stateClass = 'bg-red-500 text-white'; // Hit ship part
      displayChar = 'X';
      break;
    case 'miss':
      stateClass = 'bg-gray-400 text-gray-800'; // Missed shot
      displayChar = 'O';
      break;
    case 'killed':
      stateClass = 'bg-red-700 text-white'; // Sunk ship part
      displayChar = 'X';
      break;
    case 'ship':
      stateClass = 'bg-blue-600 text-white'; // Unhit ship part on own board
      displayChar = 'S';
      break;
    case 'occupied':
      stateClass = 'bg-gray-200 text-gray-500'; // No placement zone
      displayChar = '.';
      break;
    default: // 'empty'
      stateClass = 'bg-blue-300 text-blue-900'; // Empty water
      displayChar = '~';
      break;
  }

  // Apply hover effects during ship placement
  if (isPlacing && isHovered) {
    if (cell.canPlaceShip && !cell.isPartOfShip) {
      stateClass = 'bg-green-400 border-2 border-green-700'; // Valid placement highlight
    } else {
      stateClass = 'bg-red-400 border-2 border-red-700'; // Invalid placement highlight
    }
  }

  return (
    <div
      className={`flex items-center justify-center w-8 h-8 md:w-10 md:h-10 border border-blue-400 rounded-sm cursor-pointer transition-colors duration-100 ${stateClass}`}
      onClick={() => onClick(cell)} // Handle click event
    >
      <span className="font-bold text-sm md:text-base">{displayChar}</span>
    </div>
  );
};

export default CellComponent;
