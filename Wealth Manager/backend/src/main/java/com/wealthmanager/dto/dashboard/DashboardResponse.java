package com.wealthmanager.dto.dashboard;

import com.wealthmanager.dto.goal.GoalResponse;
import com.wealthmanager.dto.planning.EmergencyFundResponse;

import java.util.List;

public record DashboardResponse(
    MonthlySnapshotResponse monthlySnapshot,
    FinancialHealthResponse financialHealth,
    EmergencyFundResponse emergencyFund,
    List<ChartSlice> expenseBreakdown,
    List<IncomeExpensePoint> incomeVsExpense,
    List<NetWorthPoint> netWorthTrend,
    List<ChartSlice> portfolioAllocation,
    List<GoalResponse> goals,
    List<String> smartInsights
) {
}

