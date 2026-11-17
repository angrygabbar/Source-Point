export type GoalType =
  | 'EMERGENCY_FUND'
  | 'HOUSE_PURCHASE'
  | 'CAR_PURCHASE'
  | 'RETIREMENT_FUND'
  | 'VACATION'
  | 'CHILD_EDUCATION'
  | 'CUSTOM';

export type InvestmentType = 'MUTUAL_FUND' | 'STOCK' | 'FD' | 'PPF' | 'EPF' | 'NPS' | 'OTHER';

export type BudgetCategory =
  | 'EMI'
  | 'RENT'
  | 'GROCERY'
  | 'FOOD'
  | 'UTILITIES'
  | 'FUEL'
  | 'ENTERTAINMENT'
  | 'SHOPPING'
  | 'TRAVEL'
  | 'INSURANCE'
  | 'MEDICAL'
  | 'MISCELLANEOUS';

export type BudgetStatus = 'ON_TRACK' | 'WARNING' | 'OVER_BUDGET';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  age: number | null;
  maritalStatus: string;
}

export interface MonthlyFinance {
  id: string;
  month: string;
  salary: number;
  bonus: number;
  freelanceIncome: number;
  otherIncome: number;
  emi: number;
  rent: number;
  grocery: number;
  food: number;
  utilities: number;
  fuel: number;
  entertainment: number;
  shopping: number;
  travel: number;
  insurance: number;
  medical: number;
  miscellaneous: number;
  sipMonthlyContribution: number;
  sipCurrentValue: number;
  stockInvestmentAmount: number;
  stockCurrentValue: number;
  epfValue: number;
  ppfValue: number;
  npsValue: number;
  fixedDepositValue: number;
  otherInvestments: number;
  savingsAccountBalance: number;
  emergencyFundBalance: number;
  houseFundBalance: number;
  homeLoan: number;
  personalLoan: number;
  vehicleLoan: number;
  creditCardOutstanding: number;
  otherLoan: number;
  totalIncome: number;
  totalExpenses: number;
  totalSavings: number;
  savingsRate: number;
  netWorth: number;
}

export type MonthlyFinancePayload = Omit<
  MonthlyFinance,
  'id' | 'totalIncome' | 'totalExpenses' | 'totalSavings' | 'savingsRate' | 'netWorth'
>;

export interface Goal {
  id: string;
  goalType: GoalType;
  goalName: string;
  targetAmount: number;
  currentAmount: number;
  targetDate: string;
  monthlyContribution: number;
  progressPercentage: number;
  remainingAmount: number;
  estimatedCompletionDate: string | null;
}

export type GoalPayload = Omit<Goal, 'id' | 'progressPercentage' | 'remainingAmount' | 'estimatedCompletionDate'>;

export interface Investment {
  id: string;
  investmentType: InvestmentType;
  investmentName: string;
  investedAmount: number;
  currentValue: number;
  quantity: number | null;
  averagePrice: number | null;
  returnsAmount: number;
  returnsPercentage: number;
}

export type InvestmentPayload = Omit<Investment, 'id' | 'returnsAmount' | 'returnsPercentage'>;

export interface Loan {
  id: string;
  loanName: string;
  outstandingAmount: number;
  interestRate: number;
  emi: number;
  remainingTenureMonths: number;
  totalInterestRemaining: number;
  debtToIncomeRatio: number;
  projectedClosureDate: string;
}

export type LoanPayload = Pick<Loan, 'loanName' | 'outstandingAmount' | 'interestRate' | 'emi' | 'remainingTenureMonths'>;

export interface PrepaymentSimulation {
  originalOutstanding: number;
  revisedOutstanding: number;
  originalTenureMonths: number;
  revisedTenureMonths: number;
  interestSaved: number;
  revisedClosureDate: string;
}

export interface ChartSlice {
  label: string;
  value: number;
}

export interface IncomeExpensePoint {
  month: string;
  income: number;
  expenses: number;
  savings: number;
}

export interface NetWorthPoint {
  month: string;
  netWorth: number;
}

export interface ScoreBreakdownItem {
  label: string;
  value: number;
  max: number;
}

export interface EmergencyFund {
  monthlyExpenses: number;
  targetMonths: number;
  requiredEmergencyFund: number;
  currentEmergencyFund: number;
  gap: number;
  progressPercentage: number;
}

export interface Dashboard {
  monthlySnapshot: {
    monthlySalary: number;
    totalExpenses: number;
    totalSavings: number;
    savingsRate: number;
    emergencyFundBalance: number;
    houseFundBalance: number;
    sipInvestmentValue: number;
    stockPortfolioValue: number;
    loanOutstanding: number;
    netWorth: number;
  };
  financialHealth: {
    score: number;
    breakdown: ScoreBreakdownItem[];
  };
  emergencyFund: EmergencyFund;
  expenseBreakdown: ChartSlice[];
  incomeVsExpense: IncomeExpensePoint[];
  netWorthTrend: NetWorthPoint[];
  portfolioAllocation: ChartSlice[];
  goals: Goal[];
  smartInsights: string[];
}

export interface HousePurchasePayload {
  propertyCost: number;
  downPaymentTargetPercentage: number;
  existingDownPaymentFund: number;
  monthlyContribution: number;
}

export interface HousePurchaseResult {
  propertyCost: number;
  requiredDownPayment: number;
  existingDownPaymentFund: number;
  gap: number;
  monthlyContribution: number;
  monthsNeeded: number;
  estimatedCompletionDate: string;
  monthlySavingsRequiredForTwelveMonths: number;
}

export interface RetirementPlanPayload {
  currentAge: number;
  retirementAge: number;
  monthlyInvestment: number;
  expectedAnnualReturn: number;
  existingRetirementCorpus: number;
  targetRetirementCorpus: number;
}

export interface RetirementProjectionPoint {
  age: number;
  projectedCorpus: number;
}

export interface RetirementPlanResult {
  yearsToRetirement: number;
  futureCorpus: number;
  monthlySipNeeded: number;
  retirementReadinessScore: number;
  projections: RetirementProjectionPoint[];
}

export interface MonthlyReportPoint {
  month: string;
  income: number;
  expenses: number;
  savings: number;
  investments: number;
  netWorth: number;
}

export interface Reports {
  monthlyReports: MonthlyReportPoint[];
  investmentReports: MonthlyReportPoint[];
  wealthReports: MonthlyReportPoint[];
}

export interface Budget {
  id: string;
  month: string;
  category: BudgetCategory;
  limitAmount: number;
  alertThresholdPercentage: number;
  notes: string | null;
  spentAmount: number;
  remainingAmount: number;
  utilizationPercentage: number;
  status: BudgetStatus;
}

export interface BudgetPayload {
  month: string;
  category: BudgetCategory;
  limitAmount: number;
  alertThresholdPercentage: number;
  notes: string | null;
}

export interface BudgetSummary {
  month: string;
  totalBudget: number;
  totalSpent: number;
  totalRemaining: number;
  utilizationPercentage: number;
  warningCount: number;
  overBudgetCount: number;
  budgets: Budget[];
}
