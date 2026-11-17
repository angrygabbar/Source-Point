package com.wealthmanager.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(
    name = "monthly_finance",
    uniqueConstraints = @UniqueConstraint(name = "uk_monthly_finance_user_month", columnNames = {"user_id", "month"}),
    indexes = {
        @Index(name = "idx_monthly_finance_user_month", columnList = "user_id, month"),
        @Index(name = "idx_monthly_finance_user_created", columnList = "user_id, created_at")
    }
)
public class MonthlyFinance extends BaseAuditableEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false)
    private LocalDate month;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal salary;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal bonus;

    @Column(name = "freelance_income", nullable = false, precision = 15, scale = 2)
    private BigDecimal freelanceIncome;

    @Column(name = "other_income", nullable = false, precision = 15, scale = 2)
    private BigDecimal otherIncome;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal emi;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal rent;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal grocery;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal food;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal utilities;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal fuel;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal entertainment;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal shopping;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal travel;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal insurance;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal medical;

    @Column(nullable = false, precision = 15, scale = 2)
    private BigDecimal miscellaneous;

    @Column(name = "sip_monthly_contribution", nullable = false, precision = 15, scale = 2)
    private BigDecimal sipMonthlyContribution;

    @Column(name = "sip_current_value", nullable = false, precision = 15, scale = 2)
    private BigDecimal sipCurrentValue;

    @Column(name = "stock_investment_amount", nullable = false, precision = 15, scale = 2)
    private BigDecimal stockInvestmentAmount;

    @Column(name = "stock_current_value", nullable = false, precision = 15, scale = 2)
    private BigDecimal stockCurrentValue;

    @Column(name = "epf_value", nullable = false, precision = 15, scale = 2)
    private BigDecimal epfValue;

    @Column(name = "ppf_value", nullable = false, precision = 15, scale = 2)
    private BigDecimal ppfValue;

    @Column(name = "nps_value", nullable = false, precision = 15, scale = 2)
    private BigDecimal npsValue;

    @Column(name = "fixed_deposit_value", nullable = false, precision = 15, scale = 2)
    private BigDecimal fixedDepositValue;

    @Column(name = "other_investments", nullable = false, precision = 15, scale = 2)
    private BigDecimal otherInvestments;

    @Column(name = "savings_account_balance", nullable = false, precision = 15, scale = 2)
    private BigDecimal savingsAccountBalance;

    @Column(name = "emergency_fund_balance", nullable = false, precision = 15, scale = 2)
    private BigDecimal emergencyFundBalance;

    @Column(name = "house_fund_balance", nullable = false, precision = 15, scale = 2)
    private BigDecimal houseFundBalance;

    @Column(name = "home_loan", nullable = false, precision = 15, scale = 2)
    private BigDecimal homeLoan;

    @Column(name = "personal_loan", nullable = false, precision = 15, scale = 2)
    private BigDecimal personalLoan;

    @Column(name = "vehicle_loan", nullable = false, precision = 15, scale = 2)
    private BigDecimal vehicleLoan;

    @Column(name = "credit_card_outstanding", nullable = false, precision = 15, scale = 2)
    private BigDecimal creditCardOutstanding;

    @Column(name = "other_loan", nullable = false, precision = 15, scale = 2)
    private BigDecimal otherLoan;

    @Column(name = "total_income", nullable = false, precision = 15, scale = 2)
    private BigDecimal totalIncome;

    @Column(name = "total_expenses", nullable = false, precision = 15, scale = 2)
    private BigDecimal totalExpenses;

    @Column(name = "total_savings", nullable = false, precision = 15, scale = 2)
    private BigDecimal totalSavings;

    @Column(name = "savings_rate", nullable = false, precision = 8, scale = 2)
    private BigDecimal savingsRate;

    @Column(name = "net_worth", nullable = false, precision = 15, scale = 2)
    private BigDecimal netWorth;
}
