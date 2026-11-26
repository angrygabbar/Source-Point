import type { PaletteMode } from '@mui/material';
import { alpha, createTheme } from '@mui/material/styles';

export function createAppTheme(mode: PaletteMode) {
  const dark = mode === 'dark';
  const primary = dark ? '#22d3ee' : '#007bb8';
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
        default: dark ? '#141415' : '#fafafa',
        paper: dark ? '#19191b' : '#ffffff',
      },
      text: {
        primary: dark ? '#ededed' : '#171717',
        secondary: dark ? '#a1a1a6' : '#525252',
      },
      divider: dark ? alpha('#ededed', 0.08) : alpha('#171717', 0.08),
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
      fontWeightLight: 400,
      fontWeightRegular: 400,
      fontWeightMedium: 500,
      fontWeightBold: 600,
      h1: { letterSpacing: 0 },
      h2: { letterSpacing: 0 },
      h3: { letterSpacing: 0 },
      h4: { letterSpacing: 0 },
      h5: { letterSpacing: 0 },
      h6: { letterSpacing: 0 },
      button: {
        textTransform: 'none',
        letterSpacing: 0,
        fontWeight: 500,
      },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: dark ? '#141415' : '#fafafa',
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
            '@media (pointer: coarse)': {
              minHeight: 44,
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            borderColor: dark ? alpha('#ededed', 0.08) : alpha('#171717', 0.08),
            boxShadow: dark ? 'none' : '0 1px 2px rgba(0, 0, 0, 0.05)',
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
            fontWeight: 500,
            backgroundColor: dark ? '#232325' : '#f4f4f5',
          },
          root: {
            borderColor: dark ? alpha('#ededed', 0.08) : alpha('#171717', 0.08),
          },
        },
      },
      MuiTableContainer: {
        styleOverrides: {
          root: {
            width: '100%',
            maxWidth: '100%',
            overflowX: 'auto',
          },
        },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: {
            backgroundColor: dark ? alpha('#ededed', 0.1) : '#e5e7eb',
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 5,
            fontWeight: 500,
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
