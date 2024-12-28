import React, { useEffect, useRef, useState } from 'react';

const CANVAS_WIDTH = 320;
const CANVAS_HEIGHT = 480;
const MINION_SIZE = 40;
const EGG_SIZE = 20;

const Game = () => {
  const canvasRef = useRef(null);
  const [minionX, setMinionX] = useState(CANVAS_WIDTH / 2 - MINION_SIZE / 2);
  const [items, setItems] = useState([]);
  const [score, setScore] = useState(0);
  const [lives, setLives] = useState(3);
  const [chaosMode, setChaosMode] = useState(false);
  const [gameSpeed, setGameSpeed] = useState(1);
  const [gameOver, setGameOver] = useState(false);

  // Minion movement
  const handleMove = (e) => {
    if (gameOver) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.touches ? e.touches[0].clientX : e.clientX;
    setMinionX(x - rect.left - MINION_SIZE / 2);
  };

  // Game loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    const gameLoop = setInterval(() => {
      if (gameOver) return;

      // Spawn items
      if (Math.random() < 0.02 * gameSpeed) {
        const newItem = {
          id: Date.now(),
          x: Math.random() * (CANVAS_WIDTH - EGG_SIZE),
          y: 0,
          type: Math.random() > 0.7 ? 'rotten_egg' : 'egg' // 30% chance of rotten egg
        };
        setItems((prev) => [...prev, newItem]);
      }

      // Move items
      setItems((prev) =>
        prev.map((item) => ({
          ...item,
          y: item.y + 2 * gameSpeed
        }))
      );

      // Check collisions
      setItems((prev) => {
        const remaining = [];
        prev.forEach((item) => {
          const dist = Math.hypot(
            item.x - minionX,
            item.y - (CANVAS_HEIGHT - MINION_SIZE - 10)
          );
          if (dist < 30) {
            if (item.type === 'egg') {
              setScore((prevScore) => prevScore + 10);
            } else {
              setLives((prevLives) => {
                const newLives = prevLives - 1;
                return newLives >= 0 ? newLives : 0; // Prevent negative lives
              });
              if (lives <= 1) {
                setGameOver(true);
              }
            }
          } else {
            remaining.push(item);
          }
        });
        return remaining;
      });

      // Chaos mode
      if (Math.random() < 0.01) {
        setChaosMode(true);
        setGameSpeed(3);
        setTimeout(() => {
          setChaosMode(false);
          setGameSpeed(1);
        }, 5000);
      }
    }, 16);

    return () => clearInterval(gameLoop);
  }, [minionX, gameSpeed, lives, gameOver, score]);

  // Draw game
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    const draw = () => {
      ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

      // Background
      ctx.fillStyle = chaosMode ? '#FFCCCB' : '#87CEEB'; // Subtle color change
      ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

      // Minion
      ctx.fillStyle = '#FFE135';
      ctx.fillRect(minionX, CANVAS_HEIGHT - MINION_SIZE - 10, MINION_SIZE, MINION_SIZE);

      // Items
      items.forEach((item) => {
        ctx.fillStyle = item.type === 'egg' ? '#FFFFFF' : '#FF0000';
        ctx.beginPath();
        ctx.arc(item.x + EGG_SIZE / 2, item.y + EGG_SIZE / 2, EGG_SIZE / 2, 0, Math.PI * 2);
        ctx.fill();
      });

      // Score
      ctx.fillStyle = '#000000';
      ctx.font = '20px Arial';
      ctx.fillText(`Score: ${score}`, 10, 30);

      // Lives
      ctx.fillText(`Lives: ${lives}`, 10, 60);

      // Game over
      if (gameOver) {
        ctx.fillStyle = '#000000';
        ctx.font = '30px Arial';
        ctx.fillText('Game Over!', CANVAS_WIDTH / 2 - 80, CANVAS_HEIGHT / 2);
      }
    };

    const animation = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animation);
  }, [minionX, items, chaosMode, score, lives, gameOver]);

  return (
    <canvas
      ref={canvasRef}
      width={CANVAS_WIDTH}
      height={CANVAS_HEIGHT}
      onTouchMove={handleMove}
      onMouseMove={handleMove}
      style={{ border: '4px solid yellow', borderRadius: '8px' }}
    />
  );
};

export default Game;