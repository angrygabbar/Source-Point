package com.wealthmanager.dto.report;

import java.math.BigDecimal;
import java.time.LocalDate;

public record MonthlyReportPoint(
    LocalDate month,
    BigDecimal income,
    BigDecimal expenses,
    BigDecimal savings,
    BigDecimal investments,
    BigDecimal netWorth
) {
}

