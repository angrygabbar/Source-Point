import { alpha, Box, Paper, Typography, useTheme } from '@mui/material';
import type { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: string;
  icon: ReactNode;
  tone?: 'blue' | 'green' | 'amber' | 'red' | 'neutral';
}

export function MetricCard({ label, value, icon, tone = 'neutral' }: MetricCardProps) {
  const theme = useTheme();
  const colors = {
    blue: theme.palette.primary.main,
    green: theme.palette.success.main,
    amber: theme.palette.warning.main,
    red: theme.palette.error.main,
    neutral: theme.palette.text.secondary,
  };
  const color = colors[tone];
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        minHeight: 118,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        overflow: 'hidden',
        '&::after': {
          content: '""',
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 3,
          backgroundColor: color,
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
        <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 700 }}>
          {label}
        </Typography>
        <Box
          sx={{
            width: 34,
            height: 34,
            borderRadius: 1,
            display: 'grid',
            placeItems: 'center',
            backgroundColor: alpha(color, 0.13),
            color,
          }}
        >
          {icon}
        </Box>
      </Box>
      <Typography variant="h5" sx={{ fontWeight: 800, letterSpacing: 0 }}>
        {value}
      </Typography>
    </Paper>
  );
}
