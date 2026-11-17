package com.wealthmanager.dto.dashboard;

import java.math.BigDecimal;

public record ScoreBreakdownItem(
    String label,
    BigDecimal value,
    BigDecimal max
) {
}

