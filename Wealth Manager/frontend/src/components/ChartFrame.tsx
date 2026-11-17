import { Paper, Typography } from '@mui/material';
import type { ReactNode } from 'react';

interface ChartFrameProps {
  title: string;
  children: ReactNode;
}

export function ChartFrame({ title, children }: ChartFrameProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2, minHeight: 340, overflow: 'hidden' }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 900, mb: 2 }}>
        {title}
      </Typography>
      {children}
    </Paper>
  );
}
