package com.wealthmanager.dto.investment;

import com.wealthmanager.domain.InvestmentType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

public record InvestmentRequest(
    @NotNull InvestmentType investmentType,
    @NotBlank @Size(max = 160) String investmentName,
    @NotNull @PositiveOrZero BigDecimal investedAmount,
    @NotNull @PositiveOrZero BigDecimal currentValue,
    @PositiveOrZero BigDecimal quantity,
    @PositiveOrZero BigDecimal averagePrice
) {
}

