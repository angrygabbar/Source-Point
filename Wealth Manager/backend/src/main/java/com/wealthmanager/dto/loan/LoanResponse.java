package com.wealthmanager.dto.loan;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

public record LoanResponse(
    UUID id,
    String loanName,
    BigDecimal outstandingAmount,
    BigDecimal interestRate,
    BigDecimal emi,
    Integer remainingTenureMonths,
    BigDecimal totalInterestRemaining,
    BigDecimal debtToIncomeRatio,
    LocalDate projectedClosureDate
) {
}

