package com.wealthmanager.dto.dashboard;

import java.util.List;

public record FinancialHealthResponse(
    int score,
    List<ScoreBreakdownItem> breakdown
) {
}

