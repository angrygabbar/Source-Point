package com.wealthmanager.dto.dashboard;

import java.math.BigDecimal;

public record MonthlySnapshotResponse(
    BigDecimal monthlySalary,
    BigDecimal totalExpenses,
    BigDecimal totalSavings,
    BigDecimal savingsRate,
    BigDecimal emergencyFundBalance,
    BigDecimal houseFundBalance,
    BigDecimal sipInvestmentValue,
    BigDecimal stockPortfolioValue,
    BigDecimal loanOutstanding,
    BigDecimal netWorth
) {
}

