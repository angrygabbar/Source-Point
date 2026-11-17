import RefreshIcon from '@mui/icons-material/Refresh';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Typography,
} from '@mui/material';
import type { PaletteMode } from '@mui/material';
import { useEffect, useState } from 'react';
import { api, tokenStore } from './api';
import { Shell, type AppView } from './components/Shell';
import type { Dashboard, UserProfile } from './types';
import { AnalyticsView } from './views/AnalyticsView';
import { BudgetsView } from './views/BudgetsView';
import { DashboardView } from './views/DashboardView';
import { GoalsView } from './views/GoalsView';
import { InvestmentsView } from './views/InvestmentsView';
import { LoansView } from './views/LoansView';
import { MonthlyFinanceView } from './views/MonthlyFinanceView';
import { PlanningView } from './views/PlanningView';
import { ProfileView } from './views/ProfileView';
import { ReportsView } from './views/ReportsView';

interface AppProps {
  mode: PaletteMode;
  onToggleTheme: () => void;
}

export default function App({ mode, onToggleTheme }: AppProps) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [view, setView] = useState<AppView>('dashboard');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);

  async function loadDashboard() {
    setError(null);
    try {
      setDashboard(await api.dashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load dashboard');
    }
  }

  useEffect(() => {
    async function boot() {
      try {
        const profile = await api.me();
        setUser(profile);
        setDashboard(await api.dashboard());
      } catch (err) {
        tokenStore.clear();
        setBootError(err instanceof Error ? err.message : 'Unable to load your SourcePoint account.');
      } finally {
        setLoading(false);
      }
    }
    void boot();
  }, []);

  function logout() {
    tokenStore.clear();
    window.location.assign('/logout');
  }

  if (loading) {
    return (
      <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return (
      <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 2 }}>
        <Alert
          severity="error"
          action={<Button color="inherit" size="small" onClick={() => window.location.reload()}>Retry</Button>}
        >
          {bootError ?? 'Unable to load your SourcePoint account.'}
        </Alert>
      </Box>
    );
  }

  return (
    <Shell
      user={user}
      currentView={view}
      mode={mode}
      onViewChange={setView}
      onToggleTheme={onToggleTheme}
      onLogout={logout}
    >
      {error && (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" startIcon={<RefreshIcon />} onClick={() => void loadDashboard()}>
              Retry
            </Button>
          }
          sx={{ mb: 2 }}
        >
          {error}
        </Alert>
      )}
      {!dashboard ? (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography>Dashboard data is not available yet.</Typography>
          <Button sx={{ mt: 2 }} startIcon={<RefreshIcon />} onClick={() => void loadDashboard()}>
            Refresh
          </Button>
        </Paper>
      ) : (
        <>
          {view === 'dashboard' && <DashboardView dashboard={dashboard} />}
          {view === 'monthly' && <MonthlyFinanceView onChanged={loadDashboard} />}
          {view === 'budgets' && (
            <BudgetsView
              defaultMonth={dashboard.incomeVsExpense.at(-1)?.month ?? new Date().toISOString()}
              onChanged={loadDashboard}
            />
          )}
          {view === 'goals' && <GoalsView onChanged={loadDashboard} />}
          {view === 'investments' && <InvestmentsView onChanged={loadDashboard} />}
          {view === 'loans' && <LoansView onChanged={loadDashboard} />}
          {view === 'analytics' && <AnalyticsView dashboard={dashboard} />}
          {view === 'planning' && <PlanningView dashboard={dashboard} />}
          {view === 'reports' && <ReportsView />}
          {view === 'profile' && <ProfileView user={user} onProfileUpdated={setUser} />}
        </>
      )}
    </Shell>
  );
}
