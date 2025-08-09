import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import './App.css';

// --- IMPORTANT ---
// Replace 'localhost' with your computer's network IP address
// if you want to access the app from other devices on your network.
const SERVER_URL = process.env.IP_ADDR;

function App() {
  // State to hold the latest video frame and dog count from the server
  const [frame, setFrame] = useState('');
  const [uniqueDogCount, setUniqueDogCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Establish connection to the Socket.IO server
    const socket = io(SERVER_URL);

    // --- Event Listeners ---
    socket.on('connect', () => {
      console.log('Connected to backend!');
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from backend.');
      setIsConnected(false);
    });

    // This is the main listener. It receives data from the Python script.
    socket.on('update', (data) => {
      setFrame(data.image);
      setUniqueDogCount(data.count);
    });

    // --- Cleanup ---
    // This function runs when the component is unmounted to prevent memory leaks
    return () => {
      socket.disconnect();
    };
  }, []); // The empty array [] ensures this effect runs only once

  return (
    <div className="App">
      <header className="App-header">
        <h1>🐾 Campus Dog Detector</h1>
        <p className="status">
          Server Status:
          <span className={isConnected ? 'connected' : 'disconnected'}>
            {isConnected ? ' Connected' : ' Disconnected'}
          </span>
        </p>
      </header>
      <main className="App-main">
        <div className="video-container">
          {frame ? (
            <img src={frame} alt="Live video feed from server" />
          ) : (
            <div className="placeholder">Connecting to video stream...</div>
          )}
        </div>
        <div className="counter-container">
          <h2>Unique Dogs Spotted</h2>
          <p className="count">{uniqueDogCount}</p>
        </div>
      </main>
    </div>
  );
}

export default App;
