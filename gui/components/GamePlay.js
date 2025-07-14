// gui/components/GamePlay.js
import React from 'react';
import Board from './Board';
import '../styles/App.css'; // Import the CSS file

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
    <div className="gameplay-section">
      <h2 className="gameplay-title">{currentPlayer.name}'s Turn to Shoot!</h2>
      <div className="game-boards-grid">
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
      <p className="message-text">{message}</p>
    </div>
  );
};

export default GamePlay;
