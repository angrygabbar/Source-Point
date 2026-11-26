import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import AssessmentIcon from '@mui/icons-material/Assessment';
import DashboardIcon from '@mui/icons-material/Dashboard';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import FlagIcon from '@mui/icons-material/Flag';
import LightModeIcon from '@mui/icons-material/LightMode';
import LogoutIcon from '@mui/icons-material/Logout';
import PaidIcon from '@mui/icons-material/Paid';
import PersonIcon from '@mui/icons-material/Person';
import PriceCheckIcon from '@mui/icons-material/PriceCheck';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import SavingsIcon from '@mui/icons-material/Savings';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import {
  AppBar,
  Avatar,
  Box,
  ButtonBase,
  Chip,
  Container,
  Divider,
  IconButton,
  Tab,
  Tabs,
  Toolbar,
  Tooltip,
  Typography,
  type PaletteMode,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import type { ReactElement, ReactNode } from 'react';
import type { UserProfile } from '../types';

export type AppView =
  | 'dashboard'
  | 'monthly'
  | 'budgets'
  | 'goals'
  | 'investments'
  | 'loans'
  | 'analytics'
  | 'planning'
  | 'reports'
  | 'profile';

const views: Array<{ value: AppView; label: string; shortLabel: string; icon: ReactElement }> = [
  { value: 'dashboard', label: 'Overview', shortLabel: 'Home', icon: <DashboardIcon fontSize="small" /> },
  { value: 'monthly', label: 'Monthly finances', shortLabel: 'Monthly', icon: <PaidIcon fontSize="small" /> },
  { value: 'budgets', label: 'Budgets', shortLabel: 'Budgets', icon: <PriceCheckIcon fontSize="small" /> },
  { value: 'goals', label: 'Goals', shortLabel: 'Goals', icon: <FlagIcon fontSize="small" /> },
  { value: 'investments', label: 'Investments', shortLabel: 'Invest', icon: <TrendingUpIcon fontSize="small" /> },
  { value: 'loans', label: 'Loans', shortLabel: 'Loans', icon: <AccountBalanceWalletIcon fontSize="small" /> },
  { value: 'analytics', label: 'Analytics', shortLabel: 'Analytics', icon: <QueryStatsIcon fontSize="small" /> },
  { value: 'planning', label: 'Planning', shortLabel: 'Planning', icon: <SavingsIcon fontSize="small" /> },
  { value: 'reports', label: 'Reports', shortLabel: 'Reports', icon: <AssessmentIcon fontSize="small" /> },
  { value: 'profile', label: 'Profile', shortLabel: 'Profile', icon: <PersonIcon fontSize="small" /> },
];

interface ShellProps {
  user: UserProfile;
  currentView: AppView;
  mode: PaletteMode;
  onViewChange: (view: AppView) => void;
  onToggleTheme: () => void;
  onLogout: () => void;
  children: ReactNode;
}

export function Shell({
  user,
  currentView,
  mode,
  onViewChange,
  onToggleTheme,
  onLogout,
  children,
}: ShellProps) {
  const activeView = views.find((view) => view.value === currentView) ?? views[0];
  const initials = user.name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <Box sx={{ minHeight: '100vh', minWidth: 0, overflowX: 'hidden', backgroundColor: 'background.default' }}>
      <Box
        component="aside"
        sx={{
          display: { xs: 'none', md: 'flex' },
          position: 'fixed',
          inset: '0 auto 0 0',
          width: 244,
          p: 1.5,
          flexDirection: 'column',
          backgroundColor: 'background.paper',
          borderRight: '1px solid',
          borderColor: 'divider',
          zIndex: 1200,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, px: 1, minHeight: 62 }}>
          <Box
            sx={{
              width: 38,
              height: 38,
              borderRadius: 1,
              display: 'grid',
              placeItems: 'center',
              backgroundColor: 'primary.main',
              color: 'primary.contrastText',
            }}
          >
            <SavingsIcon />
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.15 }}>
              Wealth OS
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Personal finance system
            </Typography>
          </Box>
        </Box>

        <Divider sx={{ my: 1 }} />

        <Box component="nav" sx={{ display: 'grid', gap: 0.5, overflowY: 'auto', py: 0.5 }}>
          {views.map((view) => {
            const selected = view.value === currentView;
            return (
              <ButtonBase
                key={view.value}
                onClick={() => onViewChange(view.value)}
                sx={(theme) => ({
                  width: '100%',
                  minHeight: 42,
                  px: 1.25,
                  borderRadius: 1,
                  justifyContent: 'flex-start',
                  gap: 1.25,
                  color: selected ? 'primary.main' : 'text.secondary',
                  backgroundColor: selected ? alpha(theme.palette.primary.main, 0.1) : 'transparent',
                  border: '1px solid',
                  borderColor: selected ? alpha(theme.palette.primary.main, 0.24) : 'transparent',
                  '&:hover': {
                    backgroundColor: selected
                      ? alpha(theme.palette.primary.main, 0.14)
                      : alpha(theme.palette.text.primary, 0.05),
                  },
                })}
              >
                <Box sx={{ width: 24, height: 24, display: 'grid', placeItems: 'center', flexShrink: 0 }}>
                  {view.icon}
                </Box>
                <Typography variant="body2" sx={{ fontWeight: selected ? 900 : 700 }}>
                  {view.label}
                </Typography>
              </ButtonBase>
            );
          })}
        </Box>

        <Box sx={{ mt: 'auto', display: 'grid', gap: 1 }}>
          <Box
            sx={(theme) => ({
              p: 1.25,
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              backgroundColor: alpha(theme.palette.success.main, 0.06),
            })}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1 }}>
              <Typography variant="caption" color="text.secondary">
                System status
              </Typography>
              <Chip size="small" color="success" variant="outlined" label="Synced" />
            </Box>
          </Box>
          <ButtonBase
            onClick={() => onViewChange('profile')}
            sx={{
              minHeight: 52,
              p: 1,
              borderRadius: 1,
              justifyContent: 'flex-start',
              gap: 1,
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main', fontSize: 13, fontWeight: 600 }}>
              {initials}
            </Avatar>
            <Box sx={{ minWidth: 0, textAlign: 'left' }}>
              <Typography variant="body2" noWrap sx={{ fontWeight: 600 }}>
                {user.name}
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>
                {user.email}
              </Typography>
            </Box>
          </ButtonBase>
        </Box>
      </Box>

      <Box sx={{ ml: { xs: 0, md: '244px' }, minWidth: 0, width: { xs: '100%', md: 'calc(100% - 244px)' }, maxWidth: '100%' }}>
        <AppBar
          position="sticky"
          color="inherit"
          elevation={0}
          sx={{
            borderBottom: '1px solid',
            borderColor: 'divider',
            backgroundColor: 'background.paper',
          }}
        >
          <Toolbar sx={{ gap: 1.5, minHeight: { xs: 62, md: 68 } }}>
            <Box
              sx={{
                display: { xs: 'grid', md: 'none' },
                width: 34,
                height: 34,
                borderRadius: 1,
                placeItems: 'center',
                backgroundColor: 'primary.main',
                color: 'primary.contrastText',
                flexShrink: 0,
              }}
            >
              <SavingsIcon fontSize="small" />
            </Box>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="h6" noWrap sx={{ fontWeight: 600, lineHeight: 1.15 }}>
                {activeView.label}
              </Typography>
              <Typography variant="caption" color="text.secondary" noWrap>
                {user.name} | {user.age ?? 'Age not set'} | {user.maritalStatus}
              </Typography>
            </Box>
            <Tooltip title={mode === 'dark' ? 'Use light theme' : 'Use dark theme'}>
              <IconButton aria-label="Toggle color theme" onClick={onToggleTheme}>
                {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Sign out">
              <IconButton aria-label="Sign out" onClick={onLogout}>
                <LogoutIcon />
              </IconButton>
            </Tooltip>
          </Toolbar>

          <Box sx={{ display: { xs: 'block', md: 'none' }, px: 1, borderTop: '1px solid', borderColor: 'divider' }}>
            <Tabs
              value={currentView}
              onChange={(_, value) => onViewChange(value)}
              variant="scrollable"
              scrollButtons="auto"
              allowScrollButtonsMobile
              sx={{
                minHeight: 58,
                '& .MuiTabs-scrollButtons': { width: 28 },
                '& .MuiTabs-indicator': { height: 2 },
              }}
            >
              {views.map((view) => (
                <Tab
                  key={view.value}
                  value={view.value}
                  label={view.shortLabel}
                  icon={view.icon}
                  iconPosition="top"
                  aria-label={view.label}
                  sx={{
                    minWidth: 70,
                    minHeight: 58,
                    px: 0.75,
                    py: 0.5,
                    fontSize: '0.68rem',
                    lineHeight: 1.1,
                    '& .MuiTab-iconWrapper': { mb: 0.25 },
                  }}
                />
              ))}
            </Tabs>
          </Box>
        </AppBar>

        <Container
          maxWidth="xl"
          sx={{ minWidth: 0, width: '100%', maxWidth: '100%', overflowX: 'hidden', py: { xs: 1.5, sm: 2, md: 3 }, px: { xs: 1, sm: 2.5, lg: 3 } }}
        >
          {children}
        </Container>
      </Box>
    </Box>
  );
}
