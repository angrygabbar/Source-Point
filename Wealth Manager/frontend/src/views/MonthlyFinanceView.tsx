import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import RefreshIcon from '@mui/icons-material/Refresh';
import SaveIcon from '@mui/icons-material/Save';
import {
  Alert,
  Box,
  Button,
  IconButton,
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
import { SectionHeader } from '../components/SectionHeader';
import type { MonthlyFinance, MonthlyFinancePayload } from '../types';
import { formatCurrency, formatPercent, monthLabel } from '../utils/format';

type MonthlyForm = Record<keyof MonthlyFinancePayload, string>;

const moneyKeys: Array<Exclude<keyof MonthlyFinancePayload, 'month'>> = [
  'salary',
  'bonus',
  'freelanceIncome',
  'otherIncome',
  'emi',
  'rent',
  'grocery',
  'food',
  'utilities',
  'fuel',
  'entertainment',
  'shopping',
  'travel',
  'insurance',
  'medical',
  'miscellaneous',
  'sipMonthlyContribution',
  'sipCurrentValue',
  'stockInvestmentAmount',
  'stockCurrentValue',
  'epfValue',
  'ppfValue',
  'npsValue',
  'fixedDepositValue',
  'otherInvestments',
  'savingsAccountBalance',
  'emergencyFundBalance',
  'houseFundBalance',
  'homeLoan',
  'personalLoan',
  'vehicleLoan',
  'creditCardOutstanding',
  'otherLoan',
];

const groups: Array<{ title: string; fields: Array<{ key: keyof MonthlyForm; label: string }> }> = [
  {
    title: 'Income',
    fields: [
      { key: 'salary', label: 'Salary' },
      { key: 'bonus', label: 'Bonus' },
      { key: 'freelanceIncome', label: 'Freelance' },
      { key: 'otherIncome', label: 'Other Income' },
    ],
  },
  {
    title: 'Expenses',
    fields: [
      { key: 'emi', label: 'EMI' },
      { key: 'rent', label: 'Rent' },
      { key: 'grocery', label: 'Grocery' },
      { key: 'food', label: 'Food' },
      { key: 'utilities', label: 'Utilities' },
      { key: 'fuel', label: 'Fuel' },
      { key: 'entertainment', label: 'Entertainment' },
      { key: 'shopping', label: 'Shopping' },
      { key: 'travel', label: 'Travel' },
      { key: 'insurance', label: 'Insurance' },
      { key: 'medical', label: 'Medical' },
      { key: 'miscellaneous', label: 'Miscellaneous' },
    ],
  },
  {
    title: 'Investments',
    fields: [
      { key: 'sipMonthlyContribution', label: 'SIP Contribution' },
      { key: 'sipCurrentValue', label: 'SIP Current Value' },
      { key: 'stockInvestmentAmount', label: 'Stock Invested' },
      { key: 'stockCurrentValue', label: 'Stock Current Value' },
      { key: 'epfValue', label: 'EPF' },
      { key: 'ppfValue', label: 'PPF' },
      { key: 'npsValue', label: 'NPS' },
      { key: 'fixedDepositValue', label: 'Fixed Deposit' },
      { key: 'otherInvestments', label: 'Other Investments' },
    ],
  },
  {
    title: 'Assets And Liabilities',
    fields: [
      { key: 'savingsAccountBalance', label: 'Savings Account' },
      { key: 'emergencyFundBalance', label: 'Emergency Fund' },
      { key: 'houseFundBalance', label: 'House Fund' },
      { key: 'homeLoan', label: 'Home Loan' },
      { key: 'personalLoan', label: 'Personal Loan' },
      { key: 'vehicleLoan', label: 'Vehicle Loan' },
      { key: 'creditCardOutstanding', label: 'Credit Card' },
      { key: 'otherLoan', label: 'Other Loan' },
    ],
  },
];

function emptyForm(): MonthlyForm {
  const base = Object.fromEntries(moneyKeys.map((key) => [key, '0'])) as MonthlyForm;
  return { ...base, month: new Date().toISOString().slice(0, 10) };
}

function toPayload(form: MonthlyForm): MonthlyFinancePayload {
  return {
    month: form.month,
    ...Object.fromEntries(moneyKeys.map((key) => [key, Number(form[key] || 0)])),
  } as MonthlyFinancePayload;
}

function fromRecord(record: MonthlyFinance): MonthlyForm {
  const base = Object.fromEntries(moneyKeys.map((key) => [key, String(record[key] ?? 0)])) as MonthlyForm;
  return { ...base, month: record.month };
}

interface MonthlyFinanceViewProps {
  onChanged: () => void;
}

export function MonthlyFinanceView({ onChanged }: MonthlyFinanceViewProps) {
  const [records, setRecords] = useState<MonthlyFinance[]>([]);
  const [form, setForm] = useState<MonthlyForm>(() => emptyForm());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setRecords(await api.monthlyFinances());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load monthly records');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (editingId) {
        await api.updateMonthlyFinance(editingId, toPayload(form));
      } else {
        await api.createMonthlyFinance(toPayload(form));
      }
      setForm(emptyForm());
      setEditingId(null);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save monthly record');
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string) {
    setError(null);
    try {
      await api.deleteMonthlyFinance(id);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete monthly record');
    }
  }

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: 2 }}>
        <SectionHeader
          title={editingId ? 'Edit Monthly Finance' : 'Add Monthly Finance'}
          action={
            <Button type="button" startIcon={<RefreshIcon />} onClick={() => { setForm(emptyForm()); setEditingId(null); }}>
              Reset
            </Button>
          }
        />
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          label="Month"
          type="date"
          value={form.month}
          onChange={(event) => setForm((current) => ({ ...current, month: event.target.value }))}
          slotProps={{ inputLabel: { shrink: true } }}
          required
          sx={{ mb: 2, maxWidth: 220 }}
        />
        <Box sx={{ display: 'grid', gap: 2 }}>
          {groups.map((group) => (
            <Box key={group.title}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                {group.title}
              </Typography>
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', lg: 'repeat(4, minmax(0, 1fr))' },
                  gap: 1.5,
                }}
              >
                {group.fields.map((field) => (
                  <TextField
                    key={field.key}
                    label={field.label}
                    type="number"
                    value={form[field.key]}
                    onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.value }))}
                    slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
                  />
                ))}
              </Box>
            </Box>
          ))}
        </Box>
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" variant="contained" startIcon={editingId ? <SaveIcon /> : <AddIcon />} disabled={loading}>
            {editingId ? 'Save Changes' : 'Create Record'}
          </Button>
        </Box>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <SectionHeader title="Monthly History" action={<Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>} />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Month</TableCell>
                <TableCell align="right">Income</TableCell>
                <TableCell align="right">Expenses</TableCell>
                <TableCell align="right">Savings</TableCell>
                <TableCell align="right">Savings Rate</TableCell>
                <TableCell align="right">Net Worth</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {records.map((record) => (
                <TableRow key={record.id} hover>
                  <TableCell>{monthLabel(record.month)}</TableCell>
                  <TableCell align="right">{formatCurrency(record.totalIncome)}</TableCell>
                  <TableCell align="right">{formatCurrency(record.totalExpenses)}</TableCell>
                  <TableCell align="right">{formatCurrency(record.totalSavings)}</TableCell>
                  <TableCell align="right">{formatPercent(record.savingsRate)}</TableCell>
                  <TableCell align="right">{formatCurrency(record.netWorth)}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit record">
                      <IconButton
                        aria-label="Edit record"
                        onClick={() => {
                          setEditingId(record.id);
                          setForm(fromRecord(record));
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete record">
                      <IconButton aria-label="Delete record" color="error" onClick={() => void remove(record.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
}
