import type {
  BudgetPayload,
  BudgetSummary,
  Dashboard,
  Goal,
  GoalPayload,
  HousePurchasePayload,
  HousePurchaseResult,
  Investment,
  InvestmentPayload,
  Loan,
  LoanPayload,
  MonthlyFinance,
  MonthlyFinancePayload,
  PrepaymentSimulation,
  Reports,
  RetirementPlanPayload,
  RetirementPlanResult,
  UserProfile,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/wealth-api';
const SOURCEPOINT_TOKEN_URL = '/api/v1/wealth-manager/token';
let accessToken: string | null = null;
let tokenExpiresAt = 0;
let tokenRequest: Promise<string> | null = null;

export const tokenStore = {
  clear: () => {
    accessToken = null;
    tokenExpiresAt = 0;
  },
};

async function getAccessToken(forceRefresh = false): Promise<string> {
  if (!forceRefresh && accessToken && tokenExpiresAt > Date.now() + 15_000) {
    return accessToken;
  }
  if (tokenRequest) return tokenRequest;

  tokenRequest = (async () => {
    const response = await fetch(SOURCEPOINT_TOKEN_URL, {
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
    if (response.status === 401) {
      window.location.assign(`/login_register?next=${encodeURIComponent('/wealth-manager')}`);
      throw new Error('Please sign in to SourcePoint to continue.');
    }
    if (!response.ok) {
      throw new Error(`SourcePoint sign-in could not be verified (${response.status}).`);
    }
    const result = (await response.json()) as { token: string; expiresAt: number };
    accessToken = result.token;
    tokenExpiresAt = result.expiresAt;
    return result.token;
  })();

  try {
    return await tokenRequest;
  } finally {
    tokenRequest = null;
  }
}

async function authorizedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const send = async (token: string) => {
    const headers = new Headers(options.headers);
    headers.set('Authorization', `Bearer ${token}`);
    return fetch(url, { ...options, headers, credentials: 'same-origin' });
  };

  let response = await send(await getAccessToken());
  if (response.status === 401) {
    tokenStore.clear();
    response = await send(await getAccessToken(true));
  }
  return response;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');
  const response = await authorizedFetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body.details?.length) {
        message = body.details.join(', ');
      }
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function download(path: string, filename: string) {
  const response = await authorizedFetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Download failed with status ${response.status}`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export const api = {
  me: () => request<UserProfile>('/users/me'),
  updateProfile: (payload: Pick<UserProfile, 'name' | 'age' | 'maritalStatus'>) =>
    request<UserProfile>('/users/me', { method: 'PUT', body: JSON.stringify(payload) }),
  dashboard: () => request<Dashboard>('/dashboard'),
  monthlyFinances: () => request<MonthlyFinance[]>('/monthly-finances'),
  createMonthlyFinance: (payload: MonthlyFinancePayload) =>
    request<MonthlyFinance>('/monthly-finances', { method: 'POST', body: JSON.stringify(payload) }),
  updateMonthlyFinance: (id: string, payload: MonthlyFinancePayload) =>
    request<MonthlyFinance>(`/monthly-finances/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteMonthlyFinance: (id: string) => request<void>(`/monthly-finances/${id}`, { method: 'DELETE' }),
  goals: () => request<Goal[]>('/goals'),
  createGoal: (payload: GoalPayload) => request<Goal>('/goals', { method: 'POST', body: JSON.stringify(payload) }),
  updateGoal: (id: string, payload: GoalPayload) =>
    request<Goal>(`/goals/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteGoal: (id: string) => request<void>(`/goals/${id}`, { method: 'DELETE' }),
  investments: () => request<Investment[]>('/investments'),
  createInvestment: (payload: InvestmentPayload) =>
    request<Investment>('/investments', { method: 'POST', body: JSON.stringify(payload) }),
  updateInvestment: (id: string, payload: InvestmentPayload) =>
    request<Investment>(`/investments/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteInvestment: (id: string) => request<void>(`/investments/${id}`, { method: 'DELETE' }),
  loans: () => request<Loan[]>('/loans'),
  createLoan: (payload: LoanPayload) => request<Loan>('/loans', { method: 'POST', body: JSON.stringify(payload) }),
  updateLoan: (id: string, payload: LoanPayload) =>
    request<Loan>(`/loans/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteLoan: (id: string) => request<void>(`/loans/${id}`, { method: 'DELETE' }),
  simulatePrepayment: (id: string, prepaymentAmount: number) =>
    request<PrepaymentSimulation>(`/loans/${id}/simulate-prepayment`, {
      method: 'POST',
      body: JSON.stringify({ prepaymentAmount }),
    }),
  emergencyFund: () => request('/planning/emergency-fund'),
  housePurchase: (payload: HousePurchasePayload) =>
    request<HousePurchaseResult>('/planning/house-purchase', { method: 'POST', body: JSON.stringify(payload) }),
  retirementPlan: (payload: RetirementPlanPayload) =>
    request<RetirementPlanResult>('/planning/retirement', { method: 'POST', body: JSON.stringify(payload) }),
  reports: () => request<Reports>('/reports/monthly'),
  downloadExcel: () => download('/reports/export/excel', 'wealth-report.xlsx'),
  downloadPdf: () => download('/reports/export/pdf', 'wealth-report.pdf'),
  budgetSummary: (month: string) => request<BudgetSummary>(`/budgets?month=${encodeURIComponent(month)}`),
  createBudget: (payload: BudgetPayload) =>
    request('/budgets', { method: 'POST', body: JSON.stringify(payload) }),
  updateBudget: (id: string, payload: BudgetPayload) =>
    request(`/budgets/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteBudget: (id: string) => request<void>(`/budgets/${id}`, { method: 'DELETE' }),
};
