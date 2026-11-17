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
} from '@mui/material';
import { FormEvent, useEffect, useState } from 'react';
import { api } from '../api';
import { SectionHeader } from '../components/SectionHeader';
import type { Goal, GoalPayload, GoalType } from '../types';
import { formatCurrency, formatPercent } from '../utils/format';

const goalTypes: GoalType[] = [
  'EMERGENCY_FUND',
  'HOUSE_PURCHASE',
  'CAR_PURCHASE',
  'RETIREMENT_FUND',
  'VACATION',
  'CHILD_EDUCATION',
  'CUSTOM',
];

const defaultGoal = {
  goalType: 'EMERGENCY_FUND' as GoalType,
  goalName: 'Emergency Fund',
  targetAmount: '500000',
  currentAmount: '0',
  targetDate: new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toISOString().slice(0, 10),
  monthlyContribution: '25000',
};

interface GoalsViewProps {
  onChanged: () => void;
}

export function GoalsView({ onChanged }: GoalsViewProps) {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [form, setForm] = useState(defaultGoal);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setError(null);
    try {
      setGoals(await api.goals());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load goals');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function payload(): GoalPayload {
    return {
      goalType: form.goalType,
      goalName: form.goalName,
      targetAmount: Number(form.targetAmount || 0),
      currentAmount: Number(form.currentAmount || 0),
      targetDate: form.targetDate,
      monthlyContribution: Number(form.monthlyContribution || 0),
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (editingId) {
        await api.updateGoal(editingId, payload());
      } else {
        await api.createGoal(payload());
      }
      setForm(defaultGoal);
      setEditingId(null);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save goal');
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string) {
    try {
      await api.deleteGoal(id);
      await load();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete goal');
    }
  }

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: 2 }}>
        <SectionHeader
          title={editingId ? 'Edit Goal' : 'Create Goal'}
          action={<Button startIcon={<RefreshIcon />} onClick={() => { setForm(defaultGoal); setEditingId(null); }}>Reset</Button>}
        />
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' }, gap: 1.5 }}>
          <TextField
            select
            label="Goal Type"
            value={form.goalType}
            onChange={(event) => setForm((current) => ({ ...current, goalType: event.target.value as GoalType }))}
          >
            {goalTypes.map((type) => (
              <MenuItem key={type} value={type}>
                {type.replaceAll('_', ' ')}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Goal Name"
            value={form.goalName}
            onChange={(event) => setForm((current) => ({ ...current, goalName: event.target.value }))}
            required
          />
          <TextField
            label="Target Date"
            type="date"
            value={form.targetDate}
            onChange={(event) => setForm((current) => ({ ...current, targetDate: event.target.value }))}
            slotProps={{ inputLabel: { shrink: true } }}
            required
          />
          <TextField
            label="Target Amount"
            type="number"
            value={form.targetAmount}
            onChange={(event) => setForm((current) => ({ ...current, targetAmount: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            required
          />
          <TextField
            label="Current Amount"
            type="number"
            value={form.currentAmount}
            onChange={(event) => setForm((current) => ({ ...current, currentAmount: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            required
          />
          <TextField
            label="Monthly Contribution"
            type="number"
            value={form.monthlyContribution}
            onChange={(event) => setForm((current) => ({ ...current, monthlyContribution: event.target.value }))}
            slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            required
          />
        </Box>
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" variant="contained" startIcon={editingId ? <SaveIcon /> : <AddIcon />} disabled={loading}>
            {editingId ? 'Save Goal' : 'Add Goal'}
          </Button>
        </Box>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <SectionHeader title="Goals" action={<Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>} />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Goal</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Target</TableCell>
                <TableCell align="right">Current</TableCell>
                <TableCell align="right">Progress</TableCell>
                <TableCell align="right">Monthly</TableCell>
                <TableCell align="right">ETA</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {goals.map((goal) => (
                <TableRow key={goal.id} hover>
                  <TableCell>{goal.goalName}</TableCell>
                  <TableCell>{goal.goalType.replaceAll('_', ' ')}</TableCell>
                  <TableCell align="right">{formatCurrency(goal.targetAmount)}</TableCell>
                  <TableCell align="right">{formatCurrency(goal.currentAmount)}</TableCell>
                  <TableCell align="right" sx={{ minWidth: 160 }}>
                    {formatPercent(goal.progressPercentage)}
                    <LinearProgress variant="determinate" value={goal.progressPercentage} sx={{ height: 8, borderRadius: 1, mt: 0.5 }} />
                  </TableCell>
                  <TableCell align="right">{formatCurrency(goal.monthlyContribution)}</TableCell>
                  <TableCell align="right">{goal.estimatedCompletionDate ?? '-'}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Edit goal">
                      <IconButton
                        aria-label="Edit goal"
                        onClick={() => {
                          setEditingId(goal.id);
                          setForm({
                            goalType: goal.goalType,
                            goalName: goal.goalName,
                            targetAmount: String(goal.targetAmount),
                            currentAmount: String(goal.currentAmount),
                            targetDate: goal.targetDate,
                            monthlyContribution: String(goal.monthlyContribution),
                          });
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete goal">
                      <IconButton aria-label="Delete goal" color="error" onClick={() => void remove(goal.id)}>
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
