import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import RefreshIcon from '@mui/icons-material/Refresh';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import SaveIcon from '@mui/icons-material/Save';
import {
  Alert,
  Box,
  Button,
  Chip,
  IconButton,
  LinearProgress,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api';
import { MetricCard } from '../components/MetricCard';
import { SectionHeader } from '../components/SectionHeader';
import type { Budget, BudgetCategory, BudgetPayload, BudgetSummary } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import PaymentsIcon from '@mui/icons-material/Payments';

const categories: BudgetCategory[] = [
  'EMI',
  'RENT',
  'GROCERY',
  'FOOD',
  'UTILITIES',
  'FUEL',
  'ENTERTAINMENT',
  'SHOPPING',
  'TRAVEL',
  'INSURANCE',
  'MEDICAL',
  'MISCELLANEOUS',
];

const statusColor = {
  ON_TRACK: 'success',
  WARNING: 'warning',
  OVER_BUDGET: 'error',
} as const;

interface BudgetsViewProps {
  defaultMonth: string;
  onChanged: () => void;
}

export function BudgetsView({ defaultMonth, onChanged }: BudgetsViewProps) {
  const initialMonth = defaultMonth.slice(0, 7);
  const [selectedMonth, setSelectedMonth] = useState(initialMonth);
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    category: 'GROCERY' as BudgetCategory,
    limitAmount: '7000',
    alertThresholdPercentage: '80',
    notes: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const monthDate = `${selectedMonth}-01`;

  async function load() {
    setError(null);
    try {
      setSummary(await api.budgetSummary(monthDate));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load budgets');
    }
  }

  useEffect(() => {
    void load();
  }, [selectedMonth]);

  function resetForm() {
    setEditingId(null);
    setForm({
      category: 'GROCERY',
      limitAmount: '7000',
      alertThresholdPercentage: '80',
      notes: '',
    });
  }

  function payload(): BudgetPayload {
    return {
      month: monthDate,
      category: form.category,
      limitAmount: Number(form.limitAmount || 0),
      alertThresholdPercentage: Number(form.alertThresholdPercentage || 0),
      notes: form.notes.trim() || null,
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (editingId) {
        await api.updateBudget(editingId, payload());
      } else {
        await api.createBudget(payload());
      }
      resetForm();
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save budget');
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string) {
    setError(null);
    try {
      await api.deleteBudget(id);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete budget');
    }
  }

  function edit(budget: Budget) {
    setEditingId(budget.id);
    setForm({
      category: budget.category,
      limitAmount: String(budget.limitAmount),
      alertThresholdPercentage: String(budget.alertThresholdPercentage),
      notes: budget.notes ?? '',
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  return (
    <Box sx={{ width: '100%', minWidth: 0, display: 'grid', gap: 3 }}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(4, minmax(0, 1fr))' },
          gap: 2,
        }}
      >
        <MetricCard label="Monthly Budget" value={formatCurrency(summary?.totalBudget)} icon={<AccountBalanceWalletIcon />} tone="blue" />
        <MetricCard label="Tracked Spend" value={formatCurrency(summary?.totalSpent)} icon={<PaymentsIcon />} tone="amber" />
        <MetricCard label="Remaining" value={formatCurrency(summary?.totalRemaining)} icon={<CheckCircleIcon />} tone="green" />
        <MetricCard label="Over Budget" value={String(summary?.overBudgetCount ?? 0)} icon={<WarningAmberIcon />} tone="red" />
      </Box>

      <Paper component="form" onSubmit={submit} variant="outlined" sx={{ minWidth: 0, p: 2 }}>
        <SectionHeader
          title={editingId ? 'Edit Category Budget' : 'Create Category Budget'}
          action={
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, maxWidth: '100%' }}>
              <TextField
                label="Budget Month"
                type="month"
                size="small"
                value={selectedMonth}
                onChange={(event) => setSelectedMonth(event.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              <Tooltip title="Reset form">
                <IconButton aria-label="Reset budget form" onClick={resetForm}>
                  <RestartAltIcon />
                </IconButton>
              </Tooltip>
            </Box>
          }
        />
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(4, minmax(0, 1fr))' }, gap: 1.5 }}>
          <TextField
            select
            label="Category"
            value={form.category}
            onChange={(event) => setForm((current) => ({ ...current, category: event.target.value as BudgetCategory }))}
          >
            {categories.map((category) => (
              <MenuItem key={category} value={category}>
                {category.replaceAll('_', ' ')}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Monthly Limit"
            type="number"
            value={form.limitAmount}
            onChange={(event) => setForm((current) => ({ ...current, limitAmount: event.target.value }))}
            slotProps={{ htmlInput: { min: 1, step: '0.01' } }}
            required
          />
          <TextField
            label="Alert At %"
            type="number"
            value={form.alertThresholdPercentage}
            onChange={(event) => setForm((current) => ({ ...current, alertThresholdPercentage: event.target.value }))}
            slotProps={{ htmlInput: { min: 1, max: 100, step: '1' } }}
            required
          />
          <TextField
            label="Notes"
            value={form.notes}
            onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
          />
        </Box>
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" variant="contained" startIcon={editingId ? <SaveIcon /> : <AddIcon />} disabled={loading}>
            {editingId ? 'Save Budget' : 'Add Budget'}
          </Button>
        </Box>
      </Paper>

      <Paper variant="outlined" sx={{ minWidth: 0, p: 2 }}>
        <SectionHeader
          title="Budget Control"
          action={
            <Button startIcon={<RefreshIcon />} onClick={load}>
              Refresh
            </Button>
          }
        />
        {summary && summary.budgets.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.75 }}>
              <Typography variant="body2" color="text.secondary">
                Overall utilization
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {formatPercent(summary.utilizationPercentage)}
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={Math.min(summary.utilizationPercentage, 100)}
              color={summary.overBudgetCount > 0 ? 'error' : summary.warningCount > 0 ? 'warning' : 'success'}
              sx={{ height: 10, borderRadius: 1 }}
            />
          </Box>
        )}
        <TableContainer sx={{ width: '100%', maxWidth: '100%', overflowX: 'auto' }}>
          <Table size="small" sx={{ minWidth: 760 }}>
            <TableHead>
              <TableRow>
                <TableCell>Category</TableCell>
                <TableCell align="right">Limit</TableCell>
                <TableCell align="right">Spent</TableCell>
                <TableCell align="right">Remaining</TableCell>
                <TableCell>Utilization</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(summary?.budgets ?? []).map((budget) => (
                <TableRow key={budget.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {budget.category.replaceAll('_', ' ')}
                    </Typography>
                    {budget.notes && (
                      <Typography variant="caption" color="text.secondary">
                        {budget.notes}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">{formatCurrency(budget.limitAmount)}</TableCell>
                  <TableCell align="right">{formatCurrency(budget.spentAmount)}</TableCell>
                  <TableCell align="right">{formatCurrency(budget.remainingAmount)}</TableCell>
                  <TableCell sx={{ minWidth: 180 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption">{formatPercent(budget.utilizationPercentage)}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Alert {formatPercent(budget.alertThresholdPercentage)}
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(budget.utilizationPercentage, 100)}
                      color={statusColor[budget.status]}
                      sx={{ height: 7, borderRadius: 1 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={statusColor[budget.status]}
                      label={budget.status.replaceAll('_', ' ')}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit budget">
                      <IconButton aria-label="Edit budget" onClick={() => edit(budget)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete budget">
                      <IconButton aria-label="Delete budget" color="error" onClick={() => void remove(budget.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        {summary?.budgets.length === 0 && (
          <Box sx={{ py: 5, textAlign: 'center' }}>
            <Typography color="text.secondary">No category budgets exist for this month.</Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
}
