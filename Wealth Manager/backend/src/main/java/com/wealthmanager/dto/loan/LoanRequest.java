package com.wealthmanager.dto.loan;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

public record LoanRequest(
    @NotBlank @Size(max = 160) String loanName,
    @NotNull @PositiveOrZero BigDecimal outstandingAmount,
    @NotNull @PositiveOrZero @DecimalMax("100.0") BigDecimal interestRate,
    @NotNull @Positive BigDecimal emi,
    @NotNull @Positive Integer remainingTenureMonths
) {
}

