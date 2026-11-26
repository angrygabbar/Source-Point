import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import PaidIcon from '@mui/icons-material/Paid';
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
import type { Loan, LoanPayload, PrepaymentSimulation } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';

const defaultLoan = {
  loanName: 'Personal Loan',
  outstandingAmount: '850000',
  interestRate: '11',
  emi: '40000',
  remainingTenureMonths: '24',
};

interface LoansViewProps {
  onChanged: () => void;
}

export function LoansView({ onChanged }: LoansViewProps) {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [form, setForm] = useState(defaultLoan);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [prepaymentAmount, setPrepaymentAmount] = useState('50000');
  const [simulation, setSimulation] = useState<PrepaymentSimulation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setError(null);
    try {
      setLoans(await api.loans());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load loans');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function payload(): LoanPayload {
    return {
      loanName: form.loanName,
      outstandingAmount: Number(form.outstandingAmount || 0),
      interestRate: Number(form.interestRate || 0),
      emi: Number(form.emi || 0),
      remainingTenureMonths: Number(form.remainingTenureMonths || 0),
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (editingId) {
        await api.updateLoan(editingId, payload());
      } else {
        await api.createLoan(payload());
      }
      setForm(defaultLoan);
      setEditingId(null);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save loan');
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string) {
    try {
      await api.deleteLoan(id);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete loan');
    }
  }

  async function simulate(id: string) {
    setError(null);
    try {
      setSimulation(await api.simulatePrepayment(id, Number(prepaymentAmount || 0)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to simulate prepayment');
    }
  }

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: 2 }}>
        <SectionHeader
          title={editingId ? 'Edit Loan' : 'Add Loan'}
          action={<Button startIcon={<RefreshIcon />} onClick={() => { setForm(defaultLoan); setEditingId(null); }}>Reset</Button>}
        />
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(5, minmax(0, 1fr))' }, gap: 1.5 }}>
          <TextField
            label="Loan Name"
            value={form.loanName}
            onChange={(event) => setForm((current) => ({ ...current, loanName: event.target.value }))}
            required
          />
          <TextField
            label="Outstanding"
            type="number"
            value={form.outstandingAmount}
            onChange={(event) => setForm((current) => ({ ...current, outstandingAmount: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            required
          />
          <TextField
            label="Interest Rate %"
            type="number"
            value={form.interestRate}
            onChange={(event) => setForm((current) => ({ ...current, interestRate: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, max: 100, step: '0.01' } }}
            required
          />
          <TextField
            label="EMI"
            type="number"
            value={form.emi}
            onChange={(event) => setForm((current) => ({ ...current, emi: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            required
          />
          <TextField
            label="Tenure Months"
            type="number"
            value={form.remainingTenureMonths}
            onChange={(event) => setForm((current) => ({ ...current, remainingTenureMonths: event.target.value }))}
            slotProps={{ htmlInput: { min: 1, step: 1 } }}
            required
          />
        </Box>
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" variant="contained" startIcon={editingId ? <SaveIcon /> : <AddIcon />} disabled={loading}>
            {editingId ? 'Save Loan' : 'Add Loan'}
          </Button>
        </Box>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <SectionHeader title="Loans" action={<Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>} />
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
          <TextField
            label="Prepayment Amount"
            type="number"
            size="small"
            value={prepaymentAmount}
            onChange={(event) => setPrepaymentAmount(event.target.value)}
            slotProps={{ htmlInput: { min: 1, step: '0.01' } }}
            sx={{ width: 220 }}
          />
        </Box>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Loan</TableCell>
                <TableCell align="right">Outstanding</TableCell>
                <TableCell align="right">Rate</TableCell>
                <TableCell align="right">EMI</TableCell>
                <TableCell align="right">Interest Remaining</TableCell>
                <TableCell align="right">DTI</TableCell>
                <TableCell align="right">Closure</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loans.map((loan) => (
                <TableRow key={loan.id} hover>
                  <TableCell>{loan.loanName}</TableCell>
                  <TableCell align="right">{formatCurrency(loan.outstandingAmount)}</TableCell>
                  <TableCell align="right">{formatPercent(loan.interestRate)}</TableCell>
                  <TableCell align="right">{formatCurrency(loan.emi)}</TableCell>
                  <TableCell align="right">{formatCurrency(loan.totalInterestRemaining)}</TableCell>
                  <TableCell align="right">{formatPercent(loan.debtToIncomeRatio)}</TableCell>
                  <TableCell align="right">{loan.projectedClosureDate}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Simulate prepayment">
                      <IconButton aria-label="Simulate prepayment" onClick={() => void simulate(loan.id)}>
                        <PaidIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit loan">
                      <IconButton
                        aria-label="Edit loan"
                        onClick={() => {
                          setEditingId(loan.id);
                          setForm({
                            loanName: loan.loanName,
                            outstandingAmount: String(loan.outstandingAmount),
                            interestRate: String(loan.interestRate),
                            emi: String(loan.emi),
                            remainingTenureMonths: String(loan.remainingTenureMonths),
                          });
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete loan">
                      <IconButton aria-label="Delete loan" color="error" onClick={() => void remove(loan.id)}>
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

      {simulation && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
            Prepayment Simulation
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, minmax(0, 1fr))' }, gap: 1.5 }}>
            <Typography>Revised outstanding: {formatCurrency(simulation.revisedOutstanding)}</Typography>
            <Typography>Tenure reduction: {simulation.originalTenureMonths - simulation.revisedTenureMonths} months</Typography>
            <Typography>Interest saved: {formatCurrency(simulation.interestSaved)}</Typography>
          </Box>
        </Paper>
      )}
    </Box>
  );
}
