package com.wealthmanager.dto.loan;

import java.math.BigDecimal;
import java.time.LocalDate;

public record PrepaymentSimulationResponse(
    BigDecimal originalOutstanding,
    BigDecimal revisedOutstanding,
    Integer originalTenureMonths,
    Integer revisedTenureMonths,
    BigDecimal interestSaved,
    LocalDate revisedClosureDate
) {
}

