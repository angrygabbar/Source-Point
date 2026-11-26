import { Paper, Typography } from '@mui/material';
import type { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: string;
  icon: ReactNode;
  tone?: 'blue' | 'green' | 'amber' | 'red' | 'neutral';
}

export function MetricCard({ label, value }: MetricCardProps) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        minHeight: 100,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: 1.5,
      }}
    >
      <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 400 }}>
        {label}
      </Typography>
      <Typography variant="h5" sx={{ fontWeight: 500, letterSpacing: 0, fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </Typography>
    </Paper>
  );
}
