// src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
// import './index.css'; // Удалите эту строку, если index.css был только для Tailwind

import App from '../gui'; // Импорт App из вашей новой папки gui

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);