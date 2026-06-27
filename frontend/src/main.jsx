// 1. Import StrictMode directly so you don't need the "React." prefix
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx'; 
// (Make sure your CSS imports, like index.css, stay here if you have them)

createRoot(document.getElementById('root')).render(
  // 2. Use <StrictMode> instead of <React.StrictMode>
  <StrictMode>
    <App />
  </StrictMode>
);