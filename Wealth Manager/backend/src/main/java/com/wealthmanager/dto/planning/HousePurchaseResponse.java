package com.wealthmanager.dto.planning;

import java.math.BigDecimal;
import java.time.LocalDate;

public record HousePurchaseResponse(
    BigDecimal propertyCost,
    BigDecimal requiredDownPayment,
    BigDecimal existingDownPaymentFund,
    BigDecimal gap,
    BigDecimal monthlyContribution,
    Integer monthsNeeded,
    LocalDate estimatedCompletionDate,
    BigDecimal monthlySavingsRequiredForTwelveMonths
) {
}

