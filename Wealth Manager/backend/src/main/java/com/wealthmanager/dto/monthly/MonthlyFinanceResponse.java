package com.wealthmanager.dto.monthly;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

public record MonthlyFinanceResponse(
    UUID id,
    LocalDate month,
    BigDecimal salary,
    BigDecimal bonus,
    BigDecimal freelanceIncome,
    BigDecimal otherIncome,
    BigDecimal emi,
    BigDecimal rent,
    BigDecimal grocery,
    BigDecimal food,
    BigDecimal utilities,
    BigDecimal fuel,
    BigDecimal entertainment,
    BigDecimal shopping,
    BigDecimal travel,
    BigDecimal insurance,
    BigDecimal medical,
    BigDecimal miscellaneous,
    BigDecimal sipMonthlyContribution,
    BigDecimal sipCurrentValue,
    BigDecimal stockInvestmentAmount,
    BigDecimal stockCurrentValue,
    BigDecimal epfValue,
    BigDecimal ppfValue,
    BigDecimal npsValue,
    BigDecimal fixedDepositValue,
    BigDecimal otherInvestments,
    BigDecimal savingsAccountBalance,
    BigDecimal emergencyFundBalance,
    BigDecimal houseFundBalance,
    BigDecimal homeLoan,
    BigDecimal personalLoan,
    BigDecimal vehicleLoan,
    BigDecimal creditCardOutstanding,
    BigDecimal otherLoan,
    BigDecimal totalIncome,
    BigDecimal totalExpenses,
    BigDecimal totalSavings,
    BigDecimal savingsRate,
    BigDecimal netWorth
) {
}

