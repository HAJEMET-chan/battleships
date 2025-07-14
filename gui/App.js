// gui/App.js
import React, { useState, useCallback } from 'react';
import { BattleField } from './logic/GameClasses';
import ShipPlacement from './components/ShipPlacement';
import GamePlay from './components/GamePlay';

// Main App Component
function App() {
  const [players, setPlayers] = useState([
    { name: 'Player 1', ownField: new BattleField(), isReady: false },
    { name: 'Player 2', ownField: new BattleField(), isReady: false }
  ]);
  const [currentPlayerIndex, setCurrentPlayerIndex] = useState(0);
  const [gamePhase, setGamePhase] = useState('placement'); // 'placement' | 'game' | 'gameOver'
  const [message, setMessage] = useState('');
  const [winner, setWinner] = useState(null);

  const currentPlayer = players[currentPlayerIndex];
  const opponentPlayer = players[1 - currentPlayerIndex];

  // Callback for when a player finishes placing their ships
  const handlePlayerReady = useCallback(() => {
    setPlayers(prevPlayers => {
      const updatedPlayers = [...prevPlayers];
      updatedPlayers[currentPlayerIndex].isReady = true;
      return updatedPlayers;
    });

    // Check if both players are ready
    if (players.every(p => p.isReady)) {
      setGamePhase('game');
      setMessage(`Game starts! ${players[0].name}'s turn.`);
    } else {
      setMessage(`${currentPlayer.name} is ready. Next player's turn to place ships.`);
      setCurrentPlayerIndex(1 - currentPlayerIndex); // Switch to next player for placement
    }
  }, [currentPlayerIndex, players, currentPlayer.name]);

  // Callback for when a shot is made during gameplay
  const handleShotMade = useCallback((shipSunk, shotMessage) => {
    setMessage(shotMessage);
    if (opponentPlayer.ownField.isGameOver()) {
      setWinner(currentPlayer.name);
      setGamePhase('gameOver');
      setMessage(`${currentPlayer.name} wins!`);
    } else if (!shipSunk) { // If it was a miss, switch turns
      setTimeout(() => {
        setMessage(`Switching to ${opponentPlayer.name}'s turn...`);
        setTimeout(() => {
          setCurrentPlayerIndex(1 - currentPlayerIndex);
          setMessage('');
        }, 1500); // Small delay before switching
      }, 1000);
    }
    // If it was a hit and ship not sunk, current player gets another turn (no switch)
  }, [currentPlayer.name, currentPlayerIndex, opponentPlayer.name, opponentPlayer.ownField]);

  // Resets the game to its initial state
  const resetGame = () => {
    setPlayers([
      { name: 'Player 1', ownField: new BattleField(), isReady: false },
      { name: 'Player 2', ownField: new BattleField(), isReady: false }
    ]);
    setCurrentPlayerIndex(0);
    setGamePhase('placement');
    setMessage('');
    setWinner(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-inter flex flex-col items-center justify-center p-4">
      <h1 className="text-4xl md:text-5xl font-extrabold mb-8 text-shadow-lg">
        Морской бой (Battleship)
      </h1>

      {gamePhase === 'placement' && (
        <ShipPlacement
          player={currentPlayer}
          onShipPlaced={handlePlayerReady}
          message={message}
          setMessage={setMessage}
        />
      )}

      {gamePhase === 'game' && (
        <GamePlay
          currentPlayer={currentPlayer}
          opponentPlayer={opponentPlayer}
          onShotMade={handleShotMade}
          message={message}
          setMessage={setMessage}
        />
      )}

      {gamePhase === 'gameOver' && (
        <div className="flex flex-col items-center p-6 bg-green-700 rounded-lg shadow-xl">
          <h2 className="text-3xl font-bold mb-4">Game Over!</h2>
          <p className="text-2xl mb-6">{winner} has won the game!</p>
          <div className="grid md:grid-cols-2 gap-8">
            <Board
              battlefield={players[0].ownField}
              playerName={players[0].name}
              isPlayerOwnBoard={true}
              onCellClick={() => {}}
            />
            <Board
              battlefield={players[1].ownField}
              playerName={players[1].name}
              isPlayerOwnBoard={true}
              onCellClick={() => {}}
            />
          </div>
          <button
            onClick={resetGame}
            className="mt-8 px-8 py-4 bg-yellow-500 text-white font-bold text-xl rounded-lg shadow-lg hover:bg-yellow-600 transition duration-200"
          >
            Play Again
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
