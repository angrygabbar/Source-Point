package com.wealthmanager.dto.budget;

import com.wealthmanager.domain.BudgetCategory;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.LocalDate;

public record BudgetRequest(
    @NotNull LocalDate month,
    @NotNull BudgetCategory category,
    @NotNull @Positive BigDecimal limitAmount,
    @NotNull @DecimalMin("1.0") @DecimalMax("100.0") BigDecimal alertThresholdPercentage,
    @Size(max = 300) String notes
) {
}

