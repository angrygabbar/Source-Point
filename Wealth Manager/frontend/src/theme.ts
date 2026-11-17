import type { PaletteMode } from '@mui/material';
import { alpha, createTheme } from '@mui/material/styles';

export function createAppTheme(mode: PaletteMode) {
  const dark = mode === 'dark';
  const primary = dark ? '#35c5f0' : '#007bb8';
  const secondary = dark ? '#42d392' : '#00856f';

  return createTheme({
    palette: {
      mode,
      primary: { main: primary },
      secondary: { main: secondary },
      success: { main: dark ? '#42d392' : '#237a3b' },
      warning: { main: dark ? '#ffb454' : '#b05a00' },
      error: { main: dark ? '#ff7070' : '#b42318' },
      background: {
        default: dark ? '#080d14' : '#f3f6f8',
        paper: dark ? '#0e1621' : '#ffffff',
      },
      text: {
        primary: dark ? '#edf5fa' : '#132031',
        secondary: dark ? '#91a4b7' : '#5b6475',
      },
      divider: dark ? alpha('#9bc7da', 0.15) : '#dce4e9',
    },
    shape: {
      borderRadius: 8,
    },
    typography: {
      fontFamily: [
        'Inter',
        '-apple-system',
        'BlinkMacSystemFont',
        'Segoe UI',
        'sans-serif',
      ].join(','),
      h1: { letterSpacing: 0 },
      h2: { letterSpacing: 0 },
      h3: { letterSpacing: 0 },
      h4: { letterSpacing: 0 },
      h5: { letterSpacing: 0 },
      h6: { letterSpacing: 0 },
      button: {
        textTransform: 'none',
        letterSpacing: 0,
        fontWeight: 800,
      },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: dark ? '#080d14' : '#f3f6f8',
          },
          '.recharts-cartesian-axis-tick-value': {
            fill: dark ? '#91a4b7' : '#5b6475',
          },
          '.recharts-cartesian-grid line': {
            stroke: dark ? alpha('#9bc7da', 0.14) : '#dce4e9',
          },
          '.recharts-legend-item-text': {
            color: `${dark ? '#91a4b7' : '#5b6475'} !important`,
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
        styleOverrides: {
          root: {
            minHeight: 38,
            borderRadius: 6,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            borderColor: dark ? alpha('#9bc7da', 0.16) : '#dce4e9',
            boxShadow: dark ? '0 12px 36px rgba(0, 0, 0, 0.22)' : '0 8px 28px rgba(24, 48, 68, 0.06)',
          },
        },
      },
      MuiTextField: {
        defaultProps: {
          size: 'small',
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            color: dark ? '#91a4b7' : '#5b6475',
            fontWeight: 800,
            backgroundColor: dark ? '#101b28' : '#f7f9fa',
          },
          root: {
            borderColor: dark ? alpha('#9bc7da', 0.12) : '#e4eaee',
          },
        },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: {
            backgroundColor: dark ? alpha('#9bc7da', 0.12) : '#e7edf0',
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 5,
            fontWeight: 800,
          },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: {
            borderRadius: 5,
          },
        },
      },
    },
  });
}
