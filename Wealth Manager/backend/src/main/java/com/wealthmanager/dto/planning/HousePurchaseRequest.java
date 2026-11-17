package com.wealthmanager.dto.planning;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;

import java.math.BigDecimal;

public record HousePurchaseRequest(
    @NotNull @Positive BigDecimal propertyCost,
    @NotNull @Positive @DecimalMax("100.0") BigDecimal downPaymentTargetPercentage,
    @NotNull @PositiveOrZero BigDecimal existingDownPaymentFund,
    @NotNull @Positive BigDecimal monthlyContribution
) {
}

