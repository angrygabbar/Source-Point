import React, { useMemo, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { CssBaseline, ThemeProvider, type PaletteMode } from '@mui/material';
import App from './App';
import { createAppTheme } from './theme';
import './styles.css';

function Root() {
  const [mode, setMode] = useState<PaletteMode>(() => {
    const stored = localStorage.getItem('wealth-manager-theme');
    return stored === 'light' || stored === 'dark' ? stored : 'dark';
  });
  const theme = useMemo(() => createAppTheme(mode), [mode]);

  function toggleTheme() {
    setMode((current) => {
      const next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem('wealth-manager-theme', next);
      return next;
    });
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App mode={mode} onToggleTheme={toggleTheme} />
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
