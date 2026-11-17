package com.wealthmanager.dto.planning;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;

import java.math.BigDecimal;

public record RetirementPlanRequest(
    @NotNull @Min(18) @Max(80) Integer currentAge,
    @NotNull @Min(40) @Max(90) Integer retirementAge,
    @NotNull @PositiveOrZero BigDecimal monthlyInvestment,
    @NotNull @PositiveOrZero @DecimalMax("30.0") BigDecimal expectedAnnualReturn,
    @NotNull @PositiveOrZero BigDecimal existingRetirementCorpus,
    @NotNull @Positive BigDecimal targetRetirementCorpus
) {
}

