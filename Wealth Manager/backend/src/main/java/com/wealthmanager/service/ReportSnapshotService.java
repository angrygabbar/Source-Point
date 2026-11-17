package com.wealthmanager.service;

import com.wealthmanager.domain.Goal;
import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.ReportSnapshot;
import com.wealthmanager.domain.User;
import com.wealthmanager.repository.GoalRepository;
import com.wealthmanager.repository.ReportSnapshotRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ReportSnapshotService {
    private final ReportSnapshotRepository reportSnapshotRepository;
    private final GoalRepository goalRepository;

    public void refreshSnapshot(User user, MonthlyFinance finance) {
        ReportSnapshot snapshot = reportSnapshotRepository.findByUserAndMonth(user, finance.getMonth())
            .orElseGet(ReportSnapshot::new);
        snapshot.setUser(user);
        snapshot.setMonth(finance.getMonth());
        snapshot.setIncomeTotal(finance.getTotalIncome());
        snapshot.setExpenseTotal(finance.getTotalExpenses());
        snapshot.setSavingsTotal(finance.getTotalSavings());
        snapshot.setInvestmentTotal(MonthlyFinanceService.investmentTotal(finance));
        snapshot.setNetWorth(finance.getNetWorth());
        snapshot.setGoalProgressAverage(averageGoalProgress(goalRepository.findByUserOrderByTargetDateAsc(user)));
        reportSnapshotRepository.save(snapshot);
    }

    private BigDecimal averageGoalProgress(List<Goal> goals) {
        if (goals.isEmpty()) {
            return MoneyUtils.ZERO;
        }
        BigDecimal total = goals.stream()
            .map(goal -> MoneyUtils.percent(goal.getCurrentAmount(), goal.getTargetAmount()).min(MoneyUtils.ONE_HUNDRED))
            .reduce(MoneyUtils.ZERO, BigDecimal::add);
        return total.divide(BigDecimal.valueOf(goals.size()), 2, java.math.RoundingMode.HALF_UP);
    }
}

