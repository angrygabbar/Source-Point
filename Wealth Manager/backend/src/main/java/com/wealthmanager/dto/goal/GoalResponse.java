package com.wealthmanager.dto.goal;

import com.wealthmanager.domain.GoalType;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

public record GoalResponse(
    UUID id,
    GoalType goalType,
    String goalName,
    BigDecimal targetAmount,
    BigDecimal currentAmount,
    LocalDate targetDate,
    BigDecimal monthlyContribution,
    BigDecimal progressPercentage,
    BigDecimal remainingAmount,
    LocalDate estimatedCompletionDate
) {
}

