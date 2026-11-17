import DownloadIcon from '@mui/icons-material/Download';
import RefreshIcon from '@mui/icons-material/Refresh';
import {
  Alert,
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { useEffect, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../api';
import { ChartFrame } from '../components/ChartFrame';
import { SectionHeader } from '../components/SectionHeader';
import type { Reports } from '../types';
import { formatCompactCurrency, formatCurrency, monthLabel } from '../utils/format';

export function ReportsView() {
  const [reports, setReports] = useState<Reports | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setReports(await api.reports());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load reports');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function downloadExcel() {
    try {
      await api.downloadExcel();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Excel download failed');
    }
  }

  async function downloadPdf() {
    try {
      await api.downloadPdf();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PDF download failed');
    }
  }

  const rows = reports?.monthlyReports ?? [];
  const chartRows = rows.map((row) => ({ ...row, label: monthLabel(row.month) }));

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      {error && <Alert severity="error">{error}</Alert>}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <SectionHeader
          title="Reports"
          action={
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Button startIcon={<RefreshIcon />} onClick={load}>
                Refresh
              </Button>
              <Button startIcon={<DownloadIcon />} onClick={downloadExcel} variant="outlined">
                Excel
              </Button>
              <Button startIcon={<DownloadIcon />} onClick={downloadPdf} variant="outlined">
                PDF
              </Button>
            </Box>
          }
        />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Month</TableCell>
                <TableCell align="right">Income</TableCell>
                <TableCell align="right">Expenses</TableCell>
                <TableCell align="right">Savings</TableCell>
                <TableCell align="right">Investments</TableCell>
                <TableCell align="right">Net Worth</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.month} hover>
                  <TableCell>{monthLabel(row.month)}</TableCell>
                  <TableCell align="right">{formatCurrency(row.income)}</TableCell>
                  <TableCell align="right">{formatCurrency(row.expenses)}</TableCell>
                  <TableCell align="right">{formatCurrency(row.savings)}</TableCell>
                  <TableCell align="right">{formatCurrency(row.investments)}</TableCell>
                  <TableCell align="right">{formatCurrency(row.netWorth)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2 }}>
        <ChartFrame title="Income, Expense, Savings Trend">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis tickFormatter={formatCompactCurrency} />
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
              <Line type="monotone" dataKey="income" stroke="#35c5f0" strokeWidth={3} />
              <Line type="monotone" dataKey="expenses" stroke="#ffb454" strokeWidth={3} />
              <Line type="monotone" dataKey="savings" stroke="#42d392" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>
        <ChartFrame title="Investment And Wealth Growth">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis tickFormatter={formatCompactCurrency} />
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
              <Line type="monotone" dataKey="investments" stroke="#6e9fe6" strokeWidth={3} />
              <Line type="monotone" dataKey="netWorth" stroke="#35c5f0" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>
      </Box>
    </Box>
  );
}
