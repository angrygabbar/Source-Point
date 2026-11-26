import CalculateIcon from '@mui/icons-material/Calculate';
import HomeWorkIcon from '@mui/icons-material/HomeWork';
import SavingsIcon from '@mui/icons-material/Savings';
import {
  Alert,
  Box,
  Button,
  LinearProgress,
  Paper,
  Slider,
  TextField,
  Typography,
} from '@mui/material';
import { FormEvent, useState } from 'react';
import {
  CartesianGrid,
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
import type { Dashboard, HousePurchaseResult, RetirementPlanResult } from '../types';
import { formatCompactCurrency, formatCurrency, formatPercent } from '../utils/format';

interface PlanningViewProps {
  dashboard: Dashboard;
}

export function PlanningView({ dashboard }: PlanningViewProps) {
  const [houseForm, setHouseForm] = useState({
    propertyCost: '7500000',
    downPaymentTargetPercentage: '20',
    existingDownPaymentFund: String(dashboard.monthlySnapshot.houseFundBalance || 150000),
    monthlyContribution: '30000',
  });
  const [retirementForm, setRetirementForm] = useState({
    currentAge: '29',
    retirementAge: '60',
    monthlyInvestment: String(dashboard.monthlySnapshot.sipInvestmentValue > 0 ? 20000 : 15000),
    expectedAnnualReturn: 12,
    existingRetirementCorpus: String(dashboard.monthlySnapshot.sipInvestmentValue + dashboard.monthlySnapshot.stockPortfolioValue),
    targetRetirementCorpus: '30000000',
  });
  const [houseResult, setHouseResult] = useState<HousePurchaseResult | null>(null);
  const [retirementResult, setRetirementResult] = useState<RetirementPlanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function calculateHouse(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setHouseResult(
        await api.housePurchase({
          propertyCost: Number(houseForm.propertyCost || 0),
          downPaymentTargetPercentage: Number(houseForm.downPaymentTargetPercentage || 0),
          existingDownPaymentFund: Number(houseForm.existingDownPaymentFund || 0),
          monthlyContribution: Number(houseForm.monthlyContribution || 0),
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to calculate house plan');
    }
  }

  async function calculateRetirement(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setRetirementResult(
        await api.retirementPlan({
          currentAge: Number(retirementForm.currentAge || 0),
          retirementAge: Number(retirementForm.retirementAge || 0),
          monthlyInvestment: Number(retirementForm.monthlyInvestment || 0),
          expectedAnnualReturn: retirementForm.expectedAnnualReturn,
          existingRetirementCorpus: Number(retirementForm.existingRetirementCorpus || 0),
          targetRetirementCorpus: Number(retirementForm.targetRetirementCorpus || 0),
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to calculate retirement plan');
    }
  }

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper variant="outlined" sx={{ p: 2 }}>
        <SectionHeader title="Emergency Fund Tracker" action={<SavingsIcon color="primary" />} />
        <LinearProgress
          variant="determinate"
          value={dashboard.emergencyFund.progressPercentage}
          sx={{ height: 14, borderRadius: 1, mb: 1.5 }}
        />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(4, minmax(0, 1fr))' }, gap: 1.5 }}>
          <Typography>Monthly expenses: {formatCurrency(dashboard.emergencyFund.monthlyExpenses)}</Typography>
          <Typography>Target: {dashboard.emergencyFund.targetMonths} months</Typography>
          <Typography>Required: {formatCurrency(dashboard.emergencyFund.requiredEmergencyFund)}</Typography>
          <Typography>Progress: {formatPercent(dashboard.emergencyFund.progressPercentage)}</Typography>
        </Box>
      </Paper>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2 }}>
        <Paper component="form" onSubmit={calculateHouse} variant="outlined" sx={{ p: 2 }}>
          <SectionHeader title="House Purchase Planner" action={<HomeWorkIcon color="primary" />} />
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }, gap: 1.5 }}>
            <TextField
              label="Property Cost"
              type="number"
              value={houseForm.propertyCost}
              onChange={(event) => setHouseForm((current) => ({ ...current, propertyCost: event.target.value }))}
              slotProps={{ htmlInput: { min: 1, step: '0.01' } }}
            />
            <TextField
              label="Existing Down Payment Fund"
              type="number"
              value={houseForm.existingDownPaymentFund}
              onChange={(event) => setHouseForm((current) => ({ ...current, existingDownPaymentFund: event.target.value }))}
              slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            />
            <TextField
              label="Down Payment Target %"
              type="number"
              value={houseForm.downPaymentTargetPercentage}
              onChange={(event) => setHouseForm((current) => ({ ...current, downPaymentTargetPercentage: event.target.value }))}
              slotProps={{ htmlInput: { min: 1, max: 100, step: '0.01' } }}
            />
            <TextField
              label="Monthly Contribution"
              type="number"
              value={houseForm.monthlyContribution}
              onChange={(event) => setHouseForm((current) => ({ ...current, monthlyContribution: event.target.value }))}
              slotProps={{ htmlInput: { min: 1, step: '0.01' } }}
            />
          </Box>
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
            <Button type="submit" variant="contained" startIcon={<CalculateIcon />}>
              Calculate
            </Button>
          </Box>
          {houseResult && (
            <Box sx={{ mt: 2, display: 'grid', gap: 1 }}>
              <Typography>Required down payment: {formatCurrency(houseResult.requiredDownPayment)}</Typography>
              <Typography>Gap: {formatCurrency(houseResult.gap)}</Typography>
              <Typography>Time needed: {houseResult.monthsNeeded} months</Typography>
              <Typography>12-month savings required: {formatCurrency(houseResult.monthlySavingsRequiredForTwelveMonths)}</Typography>
            </Box>
          )}
        </Paper>

        <Paper component="form" onSubmit={calculateRetirement} variant="outlined" sx={{ p: 2 }}>
          <SectionHeader title="Retirement Planning" action={<SavingsIcon color="primary" />} />
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }, gap: 1.5 }}>
            <TextField
              label="Current Age"
              type="number"
              value={retirementForm.currentAge}
              onChange={(event) => setRetirementForm((current) => ({ ...current, currentAge: event.target.value }))}
              slotProps={{ htmlInput: { min: 18, max: 80 } }}
            />
            <TextField
              label="Retirement Age"
              type="number"
              value={retirementForm.retirementAge}
              onChange={(event) => setRetirementForm((current) => ({ ...current, retirementAge: event.target.value }))}
              slotProps={{ htmlInput: { min: 40, max: 90 } }}
            />
            <TextField
              label="Monthly Investment"
              type="number"
              value={retirementForm.monthlyInvestment}
              onChange={(event) => setRetirementForm((current) => ({ ...current, monthlyInvestment: event.target.value }))}
              slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            />
            <TextField
              label="Existing Corpus"
              type="number"
              value={retirementForm.existingRetirementCorpus}
              onChange={(event) => setRetirementForm((current) => ({ ...current, existingRetirementCorpus: event.target.value }))}
              slotProps={{ htmlInput: { min: 0, step: '0.01' } }}
            />
            <TextField
              label="Target Corpus"
              type="number"
              value={retirementForm.targetRetirementCorpus}
              onChange={(event) => setRetirementForm((current) => ({ ...current, targetRetirementCorpus: event.target.value }))}
              slotProps={{ htmlInput: { min: 1, step: '0.01' } }}
            />
            <Box sx={{ px: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                Expected Return: {retirementForm.expectedAnnualReturn}%
              </Typography>
              <Slider
                value={retirementForm.expectedAnnualReturn}
                min={0}
                max={20}
                step={0.5}
                onChange={(_, value) => setRetirementForm((current) => ({ ...current, expectedAnnualReturn: value as number }))}
              />
            </Box>
          </Box>
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
            <Button type="submit" variant="contained" startIcon={<CalculateIcon />}>
              Calculate
            </Button>
          </Box>
        </Paper>
      </Box>

      {retirementResult && (
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '360px 1fr' }, gap: 2 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              Retirement Readiness
            </Typography>
            <Typography variant="h3" sx={{ fontWeight: 600 }}>
              {retirementResult.retirementReadinessScore}
            </Typography>
            <Typography color="text.secondary">Future corpus: {formatCurrency(retirementResult.futureCorpus)}</Typography>
            <Typography color="text.secondary">Monthly SIP needed: {formatCurrency(retirementResult.monthlySipNeeded)}</Typography>
          </Paper>
          <ChartFrame title="Corpus Projection">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={retirementResult.projections}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="age" />
                <YAxis tickFormatter={formatCompactCurrency} />
                <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                <Line type="monotone" dataKey="projectedCorpus" stroke="#35c5f0" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartFrame>
        </Box>
      )}
    </Box>
  );
}
