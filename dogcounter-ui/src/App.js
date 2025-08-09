import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
// We'll use an icon library for better visuals
import { FiWifi, FiWifiOff } from 'react-icons/fi';

// Access the environment variable (make sure your .env file is set up)
const SERVER_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000";

function App() {
  const [frame, setFrame] = useState('');
  const [uniqueDogCount, setUniqueDogCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const socket = io(SERVER_URL);

    socket.on('connect', () => setIsConnected(true));
    socket.on('disconnect', () => setIsConnected(false));
    socket.on('update', (data) => {
      setFrame(data.image);
      setUniqueDogCount(data.count);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  // Conditional styling for the status badge
  const statusBadgeStyle = isConnected
    ? "bg-green-500/20 text-green-300"
    : "bg-red-500/20 text-red-300 animate-pulse";

  return (
    <div className="bg-gray-900 text-white min-h-screen flex flex-col items-center p-4 sm:p-8 font-sans">

      {/* --- Header --- */}
      <header className="w-full max-w-5xl flex justify-between items-center mb-8">
        <h1 className="text-2xl sm:text-4xl font-bold text-cyan-400">
          🐾 Dog Sentry
        </h1>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${statusBadgeStyle}`}>
          {isConnected ? <FiWifi /> : <FiWifiOff />}
          {isConnected ? "Connected" : "Disconnected"}
        </div>
      </header>

      {/* --- Main Content --- */}
      <main className="w-full max-w-5xl flex flex-col lg:flex-row gap-8">

        {/* --- Video Feed Section --- */}
        <div className="flex-grow bg-black rounded-xl shadow-2xl shadow-cyan-500/10 overflow-hidden border border-gray-700">
          {frame ? (
            <img src={frame} alt="Live video feed" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full min-h-[480px] flex items-center justify-center text-gray-400">
              <p>Awaiting video stream...</p>
            </div>
          )}
        </div>

        {/* --- Counter Section --- */}
        <div className="lg:w-64 flex-shrink-0 bg-gray-800/50 border border-gray-700 rounded-xl shadow-lg p-6 flex flex-col items-center justify-center">
          <h2 className="text-lg font-semibold text-gray-400 mb-2">Unique Dogs Spotted</h2>
          <p className="text-7xl font-bold text-white transition-all duration-300">
            {uniqueDogCount}
          </p>
          <p className="text-xs text-gray-500 mt-4 text-center">
            Count for {new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
      </main>

    </div>
  );
}

export default App;
