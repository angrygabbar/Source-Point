package com.wealthmanager.dto.loan;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.math.BigDecimal;

public record PrepaymentSimulationRequest(
    @NotNull @Positive BigDecimal prepaymentAmount
) {
}

