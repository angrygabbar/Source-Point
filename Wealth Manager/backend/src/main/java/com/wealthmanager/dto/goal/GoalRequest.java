package com.wealthmanager.dto.goal;

import com.wealthmanager.domain.GoalType;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.LocalDate;

public record GoalRequest(
    @NotNull GoalType goalType,
    @NotBlank @Size(max = 160) String goalName,
    @NotNull @Positive BigDecimal targetAmount,
    @NotNull @PositiveOrZero BigDecimal currentAmount,
    @NotNull @Future LocalDate targetDate,
    @NotNull @PositiveOrZero BigDecimal monthlyContribution
) {
}

