// src/index.js (or similar)
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; // Your Tailwind CSS import
import App from '../gui'; // <--- Изменено здесь

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);