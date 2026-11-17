package com.wealthmanager.dto.dashboard;

import java.math.BigDecimal;
import java.time.LocalDate;

public record NetWorthPoint(
    LocalDate month,
    BigDecimal netWorth
) {
}

