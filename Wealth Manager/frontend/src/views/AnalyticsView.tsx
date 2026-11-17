import AutoGraphIcon from '@mui/icons-material/AutoGraph';
import BoltIcon from '@mui/icons-material/Bolt';
import InsightsIcon from '@mui/icons-material/Insights';
import ShieldIcon from '@mui/icons-material/Shield';
import {
  Box,
  Chip,
  LinearProgress,
  Paper,
  Slider,
  Typography,
} from '@mui/material';
import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartFrame } from '../components/ChartFrame';
import { MetricCard } from '../components/MetricCard';
import { SectionHeader } from '../components/SectionHeader';
import type { Dashboard } from '../types';
import { formatCompactCurrency, formatCurrency, formatPercent, monthLabel } from '../utils/format';

interface AnalyticsViewProps {
  dashboard: Dashboard;
}

export function AnalyticsView({ dashboard }: AnalyticsViewProps) {
  const [horizon, setHorizon] = useState(24);
  const [annualReturn, setAnnualReturn] = useState(10);
  const [monthlySavingsBoost, setMonthlySavingsBoost] = useState(5000);
  const [extraDebtPayment, setExtraDebtPayment] = useState(5000);

  const records = dashboard.incomeVsExpense;
  const averageIncome = records.length
    ? records.reduce((sum, item) => sum + item.income, 0) / records.length
    : 0;
  const averageExpenses = records.length
    ? records.reduce((sum, item) => sum + item.expenses, 0) / records.length
    : 0;
  const averageSavings = averageIncome - averageExpenses;
  const expenseVariance = records.length
    ? records.reduce((sum, item) => sum + Math.pow(item.expenses - averageExpenses, 2), 0) / records.length
    : 0;
  const expenseVolatility = averageExpenses > 0 ? (Math.sqrt(expenseVariance) / averageExpenses) * 100 : 0;
  const emergencyRunway = averageExpenses > 0
    ? dashboard.monthlySnapshot.emergencyFundBalance / averageExpenses
    : 0;

  const forecast = useMemo(() => {
    const monthlyRate = annualReturn / 100 / 12;
    const portfolio = dashboard.portfolioAllocation.reduce((sum, item) => sum + item.value, 0);
    const startingNetWorth = dashboard.monthlySnapshot.netWorth;
    const startingDebt = dashboard.monthlySnapshot.loanOutstanding;
    const monthlyBaseSavings = Math.max(averageSavings, 0);
    let baselinePortfolio = portfolio;
    let scenarioPortfolio = portfolio;
    let baselineNetWorth = startingNetWorth;
    let scenarioNetWorth = startingNetWorth;
    let scenarioDebt = startingDebt;

    return Array.from({ length: horizon + 1 }, (_, month) => {
      if (month > 0) {
        baselinePortfolio *= 1 + monthlyRate;
        scenarioPortfolio = (scenarioPortfolio + monthlySavingsBoost) * (1 + monthlyRate);
        baselineNetWorth += monthlyBaseSavings + baselinePortfolio * monthlyRate;
        const debtReduction = Math.min(extraDebtPayment, scenarioDebt);
        scenarioDebt -= debtReduction;
        scenarioNetWorth += monthlyBaseSavings + monthlySavingsBoost + scenarioPortfolio * monthlyRate + debtReduction;
      }
      return {
        month: month === 0 ? 'Now' : `M${month}`,
        baseline: Math.round(baselineNetWorth),
        optimized: Math.round(scenarioNetWorth),
        debt: Math.round(scenarioDebt),
      };
    });
  }, [
    annualReturn,
    averageSavings,
    dashboard.monthlySnapshot.loanOutstanding,
    dashboard.monthlySnapshot.netWorth,
    dashboard.portfolioAllocation,
    extraDebtPayment,
    horizon,
    monthlySavingsBoost,
  ]);

  const cashFlowForecast = useMemo(() => {
    const lastMonth = records.at(-1)?.month ?? new Date().toISOString();
    const baseDate = new Date(lastMonth);
    return Array.from({ length: 6 }, (_, index) => {
      const date = new Date(baseDate.getFullYear(), baseDate.getMonth() + index + 1, 1);
      const seasonality = index % 3 === 2 ? 1.05 : 1;
      return {
        month: monthLabel(date.toISOString()),
        income: Math.round(averageIncome),
        expected: Math.round(averageExpenses * seasonality),
        controlled: Math.round(averageExpenses * 0.94),
      };
    });
  }, [averageExpenses, averageIncome, records]);

  const pressure = [...dashboard.expenseBreakdown]
    .filter((item) => item.value > 0)
    .sort((left, right) => right.value - left.value);
  const maxExpense = pressure[0]?.value ?? 1;
  const projectedNetWorth = forecast.at(-1)?.optimized ?? dashboard.monthlySnapshot.netWorth;
  const projectedDebt = forecast.at(-1)?.debt ?? dashboard.monthlySnapshot.loanOutstanding;

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, minmax(0, 1fr))', xl: 'repeat(4, minmax(0, 1fr))' },
          gap: 2,
        }}
      >
        <MetricCard label="Average Cash Surplus" value={formatCurrency(averageSavings)} icon={<BoltIcon />} tone="green" />
        <MetricCard label="Expense Volatility" value={formatPercent(expenseVolatility)} icon={<AutoGraphIcon />} tone="amber" />
        <MetricCard label="Emergency Runway" value={`${emergencyRunway.toFixed(1)} mo`} icon={<ShieldIcon />} tone="blue" />
        <MetricCard label={`${horizon}-Month Net Worth`} value={formatCurrency(projectedNetWorth)} icon={<InsightsIcon />} tone="neutral" />
      </Box>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <SectionHeader title="Scenario Controls" action={<Chip label="Live model" color="secondary" size="small" />} />
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(4, minmax(0, 1fr))' }, gap: 3 }}>
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 800 }}>
              Horizon: {horizon} months
            </Typography>
            <Slider value={horizon} min={6} max={60} step={6} onChange={(_, value) => setHorizon(value as number)} />
          </Box>
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 800 }}>
              Portfolio return: {annualReturn}%
            </Typography>
            <Slider value={annualReturn} min={0} max={18} step={0.5} onChange={(_, value) => setAnnualReturn(value as number)} />
          </Box>
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 800 }}>
              Savings boost: {formatCurrency(monthlySavingsBoost)}
            </Typography>
            <Slider value={monthlySavingsBoost} min={0} max={50000} step={1000} onChange={(_, value) => setMonthlySavingsBoost(value as number)} />
          </Box>
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 800 }}>
              Extra debt payment: {formatCurrency(extraDebtPayment)}
            </Typography>
            <Slider value={extraDebtPayment} min={0} max={50000} step={1000} onChange={(_, value) => setExtraDebtPayment(value as number)} />
          </Box>
        </Box>
      </Paper>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: 'minmax(0, 1.3fr) minmax(320px, 0.7fr)' }, gap: 2 }}>
        <ChartFrame title="Net Worth Scenario">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={forecast}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" interval="preserveStartEnd" />
              <YAxis tickFormatter={formatCompactCurrency} />
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
              <Area type="monotone" dataKey="baseline" stroke="#7b8798" fill="#7b8798" fillOpacity={0.12} name="Current Path" />
              <Area type="monotone" dataKey="optimized" stroke="#35c5f0" fill="#35c5f0" fillOpacity={0.16} name="Optimized Path" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartFrame>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <SectionHeader title="Scenario Outcome" />
          <Box sx={{ display: 'grid', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Projected net worth
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 900 }}>
                {formatCurrency(projectedNetWorth)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Projected debt
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 900 }}>
                {formatCurrency(projectedDebt)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Wealth acceleration
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 900 }}>
                {formatCurrency((forecast.at(-1)?.optimized ?? 0) - (forecast.at(-1)?.baseline ?? 0))}
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2 }}>
        <ChartFrame title="Six-Month Cash Flow Forecast">
          <ResponsiveContainer width="100%" height={270}>
            <LineChart data={cashFlowForecast}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={formatCompactCurrency} />
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
              <Line type="monotone" dataKey="income" stroke="#35c5f0" strokeWidth={3} name="Income" />
              <Line type="monotone" dataKey="expected" stroke="#ffb454" strokeWidth={3} name="Expected Spend" />
              <Line type="monotone" dataKey="controlled" stroke="#42d392" strokeWidth={3} name="Controlled Spend" />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame title="Expense Pressure">
          <ResponsiveContainer width="100%" height={270}>
            <BarChart data={pressure} layout="vertical" margin={{ left: 18 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={formatCompactCurrency} />
              <YAxis type="category" dataKey="label" width={92} />
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Bar dataKey="value" fill="#ffb454" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Highest category pressure
            </Typography>
            <LinearProgress variant="determinate" value={Math.min(((pressure[0]?.value ?? 0) / maxExpense) * 100, 100)} color="warning" sx={{ mt: 0.5, height: 7, borderRadius: 1 }} />
          </Box>
        </ChartFrame>
      </Box>
    </Box>
  );
}
