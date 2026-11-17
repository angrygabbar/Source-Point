package com.wealthmanager.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
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
    name = "monthly_budgets",
    uniqueConstraints = @UniqueConstraint(
        name = "uk_monthly_budgets_user_month_category",
        columnNames = {"user_id", "month", "category"}
    ),
    indexes = @Index(name = "idx_monthly_budgets_user_month", columnList = "user_id, month")
)
public class MonthlyBudget extends BaseAuditableEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false)
    private LocalDate month;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 40)
    private BudgetCategory category;

    @Column(name = "limit_amount", nullable = false, precision = 15, scale = 2)
    private BigDecimal limitAmount;

    @Column(name = "alert_threshold_percentage", nullable = false, precision = 5, scale = 2)
    private BigDecimal alertThresholdPercentage;

    @Column(length = 300)
    private String notes;
}

