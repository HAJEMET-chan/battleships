// gui/components/GamePlay.js
import React from 'react';
import Board from './Board';

const GamePlay = ({ currentPlayer, opponentPlayer, onShotMade, message, setMessage }) => {
  // Handles clicking on a cell during gameplay (to make a shot)
  const handleCellClick = (cell) => {
    // Make a shot on the opponent's board
    const result = opponentPlayer.ownField.hit(cell.x, cell.y);
    if (result.success) {
      setMessage(result.message); // Display hit/miss/sunk message
      onShotMade(result.shipSunk, result.message); // Notify parent component (App) about the shot
    } else {
      setMessage(result.message); // Display error message (e.g., already targeted)
    }
  };

  return (
    <div className="flex flex-col items-center">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">{currentPlayer.name}'s Turn to Shoot!</h2>
      <div className="grid md:grid-cols-2 gap-8">
        {/* Current Player's Own Board (ships visible, not clickable for shots) */}
        <Board
          battlefield={currentPlayer.ownField}
          playerName={currentPlayer.name}
          isPlayerOwnBoard={true}
          onCellClick={() => {}} // Own board is not clickable for shots
        />
        {/* Opponent's Board (ships hidden, clickable for shots) */}
        <Board
          battlefield={opponentPlayer.ownField}
          playerName={opponentPlayer.name}
          isPlayerOwnBoard={false}
          onCellClick={handleCellClick} // Opponent's board is clickable for shots
        />
      </div>
      <p className="mt-4 text-lg font-bold text-red-600">{message}</p>
    </div>
  );
};

export default GamePlay;
