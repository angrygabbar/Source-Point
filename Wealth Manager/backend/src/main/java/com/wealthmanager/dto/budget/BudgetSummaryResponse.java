package com.wealthmanager.dto.budget;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public record BudgetSummaryResponse(
    LocalDate month,
    BigDecimal totalBudget,
    BigDecimal totalSpent,
    BigDecimal totalRemaining,
    BigDecimal utilizationPercentage,
    long warningCount,
    long overBudgetCount,
    List<BudgetResponse> budgets
) {
}

