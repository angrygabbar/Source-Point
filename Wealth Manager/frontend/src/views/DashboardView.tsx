import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import FlagIcon from '@mui/icons-material/Flag';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import SpeedIcon from '@mui/icons-material/Speed';
import SavingsIcon from '@mui/icons-material/Savings';
import SyncIcon from '@mui/icons-material/Sync';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import {
  Box,
  Chip,
  CircularProgress,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Typography,
} from '@mui/material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
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

const chartColors = ['#35c5f0', '#42d392', '#ffb454', '#ff7070', '#6e9fe6', '#5dc2b2', '#d99b66', '#7b8798'];

interface DashboardViewProps {
  dashboard: Dashboard;
}

export function DashboardView({ dashboard }: DashboardViewProps) {
  const snapshot = dashboard.monthlySnapshot;
  const activeMonth = dashboard.incomeVsExpense.at(-1)?.month;
  const emergencyRunway = dashboard.emergencyFund.monthlyExpenses > 0
    ? dashboard.emergencyFund.currentEmergencyFund / dashboard.emergencyFund.monthlyExpenses
    : 0;
  const trend = dashboard.incomeVsExpense.map((point) => ({
    ...point,
    label: monthLabel(point.month),
  }));
  const netWorthTrend = dashboard.netWorthTrend.map((point) => ({
    ...point,
    label: monthLabel(point.month),
  }));

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      <Paper
        variant="outlined"
        sx={{
          p: { xs: 2, md: 2.5 },
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(3, minmax(0, 1fr))',
            lg: 'minmax(0, 1.3fr) repeat(3, minmax(150px, 0.4fr))',
          },
          gap: 2,
          alignItems: 'center',
          borderLeft: '3px solid',
          borderLeftColor: 'primary.main',
        }}
      >
        <Box sx={{ gridColumn: { xs: 'auto', sm: '1 / -1', lg: 'auto' } }}>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
            <Chip icon={<SyncIcon />} size="small" color="success" variant="outlined" label="Data synced" />
            {activeMonth && <Chip icon={<CalendarMonthIcon />} size="small" variant="outlined" label={monthLabel(activeMonth)} />}
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            Wealth Pulse
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Net worth {formatCurrency(snapshot.netWorth)} | Monthly surplus {formatCurrency(snapshot.totalSavings)}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Savings efficiency
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {formatPercent(snapshot.savingsRate)}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Emergency runway
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {emergencyRunway.toFixed(1)} months
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Active goals
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {dashboard.goals.length}
          </Typography>
        </Box>
      </Paper>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, minmax(0, 1fr))',
            lg: 'repeat(3, minmax(0, 1fr))',
            xl: 'repeat(6, minmax(0, 1fr))',
          },
          gap: 2,
        }}
      >
        <MetricCard label="Salary" value={formatCurrency(snapshot.monthlySalary)} icon={<SavingsIcon />} tone="blue" />
        <MetricCard label="Expenses" value={formatCurrency(snapshot.totalExpenses)} icon={<TrendingDownIcon />} tone="amber" />
        <MetricCard label="Savings" value={formatCurrency(snapshot.totalSavings)} icon={<TrendingUpIcon />} tone="green" />
        <MetricCard label="Savings Rate" value={formatPercent(snapshot.savingsRate)} icon={<SpeedIcon />} tone="blue" />
        <MetricCard label="Loans" value={formatCurrency(snapshot.loanOutstanding)} icon={<AccountBalanceWalletIcon />} tone="red" />
        <MetricCard label="Net Worth" value={formatCurrency(snapshot.netWorth)} icon={<AccountBalanceIcon />} tone="neutral" />
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '360px 1fr' }, gap: 2 }}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <SectionHeader title="Financial Health" action={<Chip label={`${dashboard.financialHealth.score}/100`} color="primary" />} />
          <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 132 }}>
            <Box sx={{ position: 'relative', display: 'inline-flex' }}>
              <CircularProgress
                variant="determinate"
                value={dashboard.financialHealth.score}
                size={116}
                thickness={5}
                color={dashboard.financialHealth.score >= 70 ? 'success' : dashboard.financialHealth.score >= 45 ? 'warning' : 'error'}
              />
              <Box sx={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center' }}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" sx={{ fontWeight: 600, lineHeight: 1 }}>
                    {dashboard.financialHealth.score}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    health score
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Box>
          <Box sx={{ display: 'grid', gap: 1.5 }}>
            {dashboard.financialHealth.breakdown.map((item) => (
              <Box key={item.label}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="body2" color="text.secondary">
                    {item.label}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {item.value.toFixed(1)} / {item.max}
                  </Typography>
                </Box>
                <LinearProgress variant="determinate" value={(item.value / item.max) * 100} sx={{ height: 8, borderRadius: 1 }} />
              </Box>
            ))}
          </Box>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <SectionHeader title="Goal And Fund Progress" />
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1, fontWeight: 500 }}>
                Emergency Fund
              </Typography>
              <LinearProgress
                variant="determinate"
                value={dashboard.emergencyFund.progressPercentage}
                sx={{ height: 12, borderRadius: 1, mb: 1 }}
              />
              <Typography variant="body2">
                {formatCurrency(dashboard.emergencyFund.currentEmergencyFund)} of{' '}
                {formatCurrency(dashboard.emergencyFund.requiredEmergencyFund)} saved
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Gap: {formatCurrency(dashboard.emergencyFund.gap)}
              </Typography>
            </Box>
            <Box sx={{ display: 'grid', gap: 1 }}>
              {dashboard.goals.slice(0, 4).map((goal) => (
                <Box key={goal.id}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {goal.goalName}
                    </Typography>
                    <Typography variant="body2">{formatPercent(goal.progressPercentage)}</Typography>
                  </Box>
                  <LinearProgress variant="determinate" value={goal.progressPercentage} sx={{ height: 8, borderRadius: 1 }} />
                </Box>
              ))}
            </Box>
          </Box>
        </Paper>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', xl: '1fr 1fr' }, gap: 2 }}>
        <ChartFrame title="Income vs Expense">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis tickFormatter={formatCompactCurrency} />
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
              <Bar dataKey="income" fill="#35c5f0" name="Income" />
              <Bar dataKey="expenses" fill="#ffb454" name="Expenses" />
              <Bar dataKey="savings" fill="#42d392" name="Savings" />
            </BarChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame title="Net Worth Growth">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={netWorthTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis tickFormatter={formatCompactCurrency} />
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Line type="monotone" dataKey="netWorth" stroke="#35c5f0" strokeWidth={3} dot={{ r: 4 }} name="Net Worth" />
            </LineChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame title="Expense Breakdown">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={dashboard.expenseBreakdown.filter((slice) => slice.value > 0)}
                dataKey="value"
                nameKey="label"
                innerRadius={54}
                outerRadius={94}
                paddingAngle={2}
              >
                {dashboard.expenseBreakdown.map((_, index) => (
                  <Cell key={index} fill={chartColors[index % chartColors.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartFrame>

        <ChartFrame title="Portfolio Allocation">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={dashboard.portfolioAllocation.filter((slice) => slice.value > 0)}
                dataKey="value"
                nameKey="label"
                outerRadius={96}
              >
                {dashboard.portfolioAllocation.map((_, index) => (
                  <Cell key={index} fill={chartColors[index % chartColors.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartFrame>
      </Box>

      <Paper variant="outlined" sx={{ p: 2, borderLeft: '3px solid', borderLeftColor: 'secondary.main' }}>
        <SectionHeader title="Smart Insights" action={<HealthAndSafetyIcon color="secondary" />} />
        <List dense disablePadding>
          {dashboard.smartInsights.map((insight) => (
            <ListItem key={insight} disablePadding sx={{ py: 0.45 }}>
              <ListItemIcon sx={{ minWidth: 32, color: 'secondary.main' }}>
                <FlagIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText primary={insight} />
            </ListItem>
          ))}
        </List>
      </Paper>
    </Box>
  );
}
