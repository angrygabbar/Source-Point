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
} from '@mui/material';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api';
import { SectionHeader } from '../components/SectionHeader';
import type { Investment, InvestmentPayload, InvestmentType } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';

const investmentTypes: InvestmentType[] = ['MUTUAL_FUND', 'STOCK', 'FD', 'PPF', 'EPF', 'NPS', 'OTHER'];

const defaultInvestment = {
  investmentType: 'MUTUAL_FUND' as InvestmentType,
  investmentName: 'Equity SIP Portfolio',
  investedAmount: '0',
  currentValue: '0',
  quantity: '',
  averagePrice: '',
};

interface InvestmentsViewProps {
  onChanged: () => void;
}

export function InvestmentsView({ onChanged }: InvestmentsViewProps) {
  const [items, setItems] = useState<Investment[]>([]);
  const [form, setForm] = useState(defaultInvestment);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setError(null);
    try {
      setItems(await api.investments());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load investments');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function payload(): InvestmentPayload {
    return {
      investmentType: form.investmentType,
      investmentName: form.investmentName,
      investedAmount: Number(form.investedAmount || 0),
      currentValue: Number(form.currentValue || 0),
      quantity: form.quantity === '' ? null : Number(form.quantity),
      averagePrice: form.averagePrice === '' ? null : Number(form.averagePrice),
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (editingId) {
        await api.updateInvestment(editingId, payload());
      } else {
        await api.createInvestment(payload());
      }
      setForm(defaultInvestment);
      setEditingId(null);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save investment');
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string) {
    try {
      await api.deleteInvestment(id);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete investment');
    }
  }

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: 2 }}>
        <SectionHeader
          title={editingId ? 'Edit Investment' : 'Add Investment'}
          action={<Button startIcon={<RefreshIcon />} onClick={() => { setForm(defaultInvestment); setEditingId(null); }}>Reset</Button>}
        />
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' }, gap: 1.5 }}>
          <TextField
            select
            label="Investment Type"
            value={form.investmentType}
            onChange={(event) => setForm((current) => ({ ...current, investmentType: event.target.value as InvestmentType }))}
          >
            {investmentTypes.map((type) => (
              <MenuItem key={type} value={type}>
                {type.replaceAll('_', ' ')}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Name"
            value={form.investmentName}
            onChange={(event) => setForm((current) => ({ ...current, investmentName: event.target.value }))}
            required
          />
          <TextField
            label="Invested Amount"
            type="number"
            value={form.investedAmount}
            onChange={(event) => setForm((current) => ({ ...current, investedAmount: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            required
          />
          <TextField
            label="Current Value"
            type="number"
            value={form.currentValue}
            onChange={(event) => setForm((current) => ({ ...current, currentValue: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            required
          />
          <TextField
            label="Quantity"
            type="number"
            value={form.quantity}
            onChange={(event) => setForm((current) => ({ ...current, quantity: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.0001' } }}
          />
          <TextField
            label="Average Price"
            type="number"
            value={form.averagePrice}
            onChange={(event) => setForm((current) => ({ ...current, averagePrice: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
          />
        </Box>
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" variant="contained" startIcon={editingId ? <SaveIcon /> : <AddIcon />} disabled={loading}>
            {editingId ? 'Save Investment' : 'Add Investment'}
          </Button>
        </Box>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <SectionHeader title="Portfolio" action={<Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>} />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Invested</TableCell>
                <TableCell align="right">Current</TableCell>
                <TableCell align="right">Returns</TableCell>
                <TableCell align="right">Return %</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell>{item.investmentName}</TableCell>
                  <TableCell>{item.investmentType.replaceAll('_', ' ')}</TableCell>
                  <TableCell align="right">{formatCurrency(item.investedAmount)}</TableCell>
                  <TableCell align="right">{formatCurrency(item.currentValue)}</TableCell>
                  <TableCell align="right">{formatCurrency(item.returnsAmount)}</TableCell>
                  <TableCell align="right">{formatPercent(item.returnsPercentage)}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit investment">
                      <IconButton
                        aria-label="Edit investment"
                        onClick={() => {
                          setEditingId(item.id);
                          setForm({
                            investmentType: item.investmentType,
                            investmentName: item.investmentName,
                            investedAmount: String(item.investedAmount),
                            currentValue: String(item.currentValue),
                            quantity: item.quantity == null ? '' : String(item.quantity),
                            averagePrice: item.averagePrice == null ? '' : String(item.averagePrice),
                          });
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete investment">
                      <IconButton aria-label="Delete investment" color="error" onClick={() => void remove(item.id)}>
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
