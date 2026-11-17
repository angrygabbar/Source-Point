package com.wealthmanager.dto.planning;

import java.math.BigDecimal;

public record EmergencyFundResponse(
    BigDecimal monthlyExpenses,
    Integer targetMonths,
    BigDecimal requiredEmergencyFund,
    BigDecimal currentEmergencyFund,
    BigDecimal gap,
    BigDecimal progressPercentage
) {
}

