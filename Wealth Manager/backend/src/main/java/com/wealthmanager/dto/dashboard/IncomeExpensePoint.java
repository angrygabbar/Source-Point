package com.wealthmanager.dto.dashboard;

import java.math.BigDecimal;
import java.time.LocalDate;

public record IncomeExpensePoint(
    LocalDate month,
    BigDecimal income,
    BigDecimal expenses,
    BigDecimal savings
) {
}

