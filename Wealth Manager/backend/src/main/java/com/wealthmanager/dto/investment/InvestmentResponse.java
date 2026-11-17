package com.wealthmanager.dto.investment;

import com.wealthmanager.domain.InvestmentType;

import java.math.BigDecimal;
import java.util.UUID;

public record InvestmentResponse(
    UUID id,
    InvestmentType investmentType,
    String investmentName,
    BigDecimal investedAmount,
    BigDecimal currentValue,
    BigDecimal quantity,
    BigDecimal averagePrice,
    BigDecimal returnsAmount,
    BigDecimal returnsPercentage
) {
}

