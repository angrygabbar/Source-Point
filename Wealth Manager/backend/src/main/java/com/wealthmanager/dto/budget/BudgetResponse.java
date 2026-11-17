package com.wealthmanager.dto.budget;

import com.wealthmanager.domain.BudgetCategory;
import com.wealthmanager.domain.BudgetStatus;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

public record BudgetResponse(
    UUID id,
    LocalDate month,
    BudgetCategory category,
    BigDecimal limitAmount,
    BigDecimal alertThresholdPercentage,
    String notes,
    BigDecimal spentAmount,
    BigDecimal remainingAmount,
    BigDecimal utilizationPercentage,
    BudgetStatus status
) {
}

