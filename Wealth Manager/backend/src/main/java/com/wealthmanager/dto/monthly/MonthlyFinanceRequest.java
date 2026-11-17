package com.wealthmanager.dto.monthly;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PastOrPresent;
import jakarta.validation.constraints.PositiveOrZero;

import java.math.BigDecimal;
import java.time.LocalDate;

public record MonthlyFinanceRequest(
    @NotNull @PastOrPresent LocalDate month,
    @PositiveOrZero BigDecimal salary,
    @PositiveOrZero BigDecimal bonus,
    @PositiveOrZero BigDecimal freelanceIncome,
    @PositiveOrZero BigDecimal otherIncome,
    @PositiveOrZero BigDecimal emi,
    @PositiveOrZero BigDecimal rent,
    @PositiveOrZero BigDecimal grocery,
    @PositiveOrZero BigDecimal food,
    @PositiveOrZero BigDecimal utilities,
    @PositiveOrZero BigDecimal fuel,
    @PositiveOrZero BigDecimal entertainment,
    @PositiveOrZero BigDecimal shopping,
    @PositiveOrZero BigDecimal travel,
    @PositiveOrZero BigDecimal insurance,
    @PositiveOrZero BigDecimal medical,
    @PositiveOrZero BigDecimal miscellaneous,
    @PositiveOrZero BigDecimal sipMonthlyContribution,
    @PositiveOrZero BigDecimal sipCurrentValue,
    @PositiveOrZero BigDecimal stockInvestmentAmount,
    @PositiveOrZero BigDecimal stockCurrentValue,
    @PositiveOrZero BigDecimal epfValue,
    @PositiveOrZero BigDecimal ppfValue,
    @PositiveOrZero BigDecimal npsValue,
    @PositiveOrZero BigDecimal fixedDepositValue,
    @PositiveOrZero BigDecimal otherInvestments,
    @PositiveOrZero BigDecimal savingsAccountBalance,
    @PositiveOrZero BigDecimal emergencyFundBalance,
    @PositiveOrZero BigDecimal houseFundBalance,
    @PositiveOrZero BigDecimal homeLoan,
    @PositiveOrZero BigDecimal personalLoan,
    @PositiveOrZero BigDecimal vehicleLoan,
    @PositiveOrZero BigDecimal creditCardOutstanding,
    @PositiveOrZero BigDecimal otherLoan
) {
}

