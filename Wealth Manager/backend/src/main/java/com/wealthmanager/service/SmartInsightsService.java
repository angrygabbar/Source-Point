package com.wealthmanager.service;

import com.wealthmanager.domain.Goal;
import com.wealthmanager.domain.GoalType;
import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.User;
import com.wealthmanager.repository.GoalRepository;
import com.wealthmanager.repository.MonthlyFinanceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service
@RequiredArgsConstructor
public class SmartInsightsService {
    private final CurrentUserService currentUserService;
    private final MonthlyFinanceRepository monthlyFinanceRepository;
    private final GoalRepository goalRepository;
    private final PlanningService planningService;
    private final BudgetService budgetService;

    @Transactional(readOnly = true)
    public List<String> list() {
        return generateForUser(currentUserService.getCurrentUser());
    }

    public List<String> generateForUser(User user) {
        List<MonthlyFinance> records = new ArrayList<>(monthlyFinanceRepository.findTop12ByUserOrderByMonthDesc(user));
        records.sort(Comparator.comparing(MonthlyFinance::getMonth).reversed());
        List<String> insights = new ArrayList<>();
        if (records.isEmpty()) {
            insights.add("Add your first monthly finance record to unlock personalized insights.");
            return insights;
        }

        MonthlyFinance latest = records.get(0);
        var budgetSummary = budgetService.summaryForUser(user, latest.getMonth());
        if (budgetSummary.overBudgetCount() > 0) {
            insights.add(budgetSummary.overBudgetCount() + " budget categories are over limit this month.");
        } else if (budgetSummary.warningCount() > 0) {
            insights.add(budgetSummary.warningCount() + " budget categories are approaching their alert threshold.");
        }

        var emergency = planningService.emergencyFund(latest.getTotalExpenses(), latest.getEmergencyFundBalance(), 6);
        if (emergency.progressPercentage().compareTo(BigDecimal.valueOf(100)) < 0) {
            insights.add("Emergency fund is below the 6-month target by " + emergency.gap());
        }

        BigDecimal emiRatio = MoneyUtils.percent(latest.getEmi(), latest.getTotalIncome());
        if (emiRatio.compareTo(BigDecimal.valueOf(35)) > 0) {
            insights.add("EMI ratio is above 35%; consider prepayments or refinancing before increasing fixed obligations.");
        }

        if (latest.getSavingsRate().compareTo(BigDecimal.valueOf(30)) < 0) {
            insights.add("Savings rate is below 30%; review flexible categories before committing to new goals.");
        }

        if (records.size() >= 2) {
            MonthlyFinance previous = records.get(1);
            BigDecimal foodIncrease = latest.getFood().subtract(previous.getFood());
            BigDecimal foodIncreaseRate = MoneyUtils.percent(foodIncrease, previous.getFood());
            if (foodIncreaseRate.compareTo(BigDecimal.valueOf(20)) >= 0) {
                insights.add("Food expenses increased by " + foodIncreaseRate + "% compared with the previous month.");
            }
        }

        goalRepository.findFirstByUserAndGoalTypeOrderByCreatedAtDesc(user, GoalType.HOUSE_PURCHASE)
            .ifPresent(goal -> addHouseGoalInsight(insights, goal));

        goalRepository.findFirstByUserAndGoalTypeOrderByCreatedAtDesc(user, GoalType.RETIREMENT_FUND)
            .ifPresent(goal -> {
                BigDecimal progress = MoneyUtils.percent(goal.getCurrentAmount(), goal.getTargetAmount());
                if (progress.compareTo(BigDecimal.valueOf(25)) < 0) {
                    insights.add("Retirement corpus is early-stage; consider increasing SIP contributions after the emergency fund is stable.");
                }
            });

        if (insights.isEmpty()) {
            insights.add("Finances look balanced this month. Keep tracking trends to catch drift early.");
        }
        return insights;
    }

    private void addHouseGoalInsight(List<String> insights, Goal goal) {
        BigDecimal remaining = MoneyUtils.subtractFloorZero(goal.getTargetAmount(), goal.getCurrentAmount());
        if (remaining.compareTo(BigDecimal.ZERO) == 0) {
            insights.add("House purchase goal is funded.");
            return;
        }
        if (goal.getMonthlyContribution().compareTo(BigDecimal.ZERO) > 0) {
            insights.add("House goal is active with a monthly contribution of " + goal.getMonthlyContribution() + ".");
        }
    }
}
