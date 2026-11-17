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
    name = "reports",
    uniqueConstraints = @UniqueConstraint(name = "uk_reports_user_month", columnNames = {"user_id", "month"}),
    indexes = @Index(name = "idx_reports_user_month", columnList = "user_id, month")
)
public class ReportSnapshot extends BaseAuditableEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false)
    private LocalDate month;

    @Column(name = "income_total", nullable = false, precision = 15, scale = 2)
    private BigDecimal incomeTotal;

    @Column(name = "expense_total", nullable = false, precision = 15, scale = 2)
    private BigDecimal expenseTotal;

    @Column(name = "savings_total", nullable = false, precision = 15, scale = 2)
    private BigDecimal savingsTotal;

    @Column(name = "investment_total", nullable = false, precision = 15, scale = 2)
    private BigDecimal investmentTotal;

    @Column(name = "net_worth", nullable = false, precision = 15, scale = 2)
    private BigDecimal netWorth;

    @Column(name = "goal_progress_average", nullable = false, precision = 8, scale = 2)
    private BigDecimal goalProgressAverage;
}

