package com.wealthmanager.service;

import com.wealthmanager.domain.Goal;
import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.User;
import com.wealthmanager.dto.dashboard.ChartSlice;
import com.wealthmanager.dto.dashboard.DashboardResponse;
import com.wealthmanager.dto.dashboard.FinancialHealthResponse;
import com.wealthmanager.dto.dashboard.IncomeExpensePoint;
import com.wealthmanager.dto.dashboard.MonthlySnapshotResponse;
import com.wealthmanager.dto.dashboard.NetWorthPoint;
import com.wealthmanager.dto.dashboard.ScoreBreakdownItem;
import com.wealthmanager.dto.goal.GoalResponse;
import com.wealthmanager.dto.planning.EmergencyFundResponse;
import com.wealthmanager.repository.GoalRepository;
import com.wealthmanager.repository.MonthlyFinanceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Service
@RequiredArgsConstructor
public class DashboardService {
    private final CurrentUserService currentUserService;
    private final MonthlyFinanceRepository monthlyFinanceRepository;
    private final GoalRepository goalRepository;
    private final GoalService goalService;
    private final PlanningService planningService;
    private final SmartInsightsService smartInsightsService;

    @Transactional(readOnly = true)
    public DashboardResponse dashboard() {
        User user = currentUserService.getCurrentUser();
        List<MonthlyFinance> records = new ArrayList<>(monthlyFinanceRepository.findTop12ByUserOrderByMonthDesc(user));
        records.sort(Comparator.comparing(MonthlyFinance::getMonth));
        MonthlyFinance latest = records.isEmpty() ? null : records.get(records.size() - 1);
        MonthlyFinance previous = records.size() > 1 ? records.get(records.size() - 2) : null;
        List<GoalResponse> goals = goalRepository.findByUserOrderByTargetDateAsc(user).stream()
            .map(goalService::toResponse)
            .toList();

        return new DashboardResponse(
            monthlySnapshot(latest),
            financialHealth(latest, previous),
            latest == null ? planningService.emergencyFund(MoneyUtils.ZERO, MoneyUtils.ZERO, 6) : planningService.emergencyFund(latest.getTotalExpenses(), latest.getEmergencyFundBalance(), 6),
            expenseBreakdown(latest),
            records.stream().map(item -> new IncomeExpensePoint(item.getMonth(), item.getTotalIncome(), item.getTotalExpenses(), item.getTotalSavings())).toList(),
            records.stream().map(item -> new NetWorthPoint(item.getMonth(), item.getNetWorth())).toList(),
            portfolioAllocation(latest),
            goals,
            smartInsightsService.generateForUser(user)
        );
    }

    private MonthlySnapshotResponse monthlySnapshot(MonthlyFinance latest) {
        if (latest == null) {
            return new MonthlySnapshotResponse(MoneyUtils.ZERO, MoneyUtils.ZERO, MoneyUtils.ZERO, MoneyUtils.ZERO, MoneyUtils.ZERO, MoneyUtils.ZERO, MoneyUtils.ZERO, MoneyUtils.ZERO, MoneyUtils.ZERO, MoneyUtils.ZERO);
        }
        return new MonthlySnapshotResponse(
            latest.getSalary(),
            latest.getTotalExpenses(),
            latest.getTotalSavings(),
            latest.getSavingsRate(),
            latest.getEmergencyFundBalance(),
            latest.getHouseFundBalance(),
            latest.getSipCurrentValue(),
            latest.getStockCurrentValue(),
            MonthlyFinanceService.liabilityTotal(latest),
            latest.getNetWorth()
        );
    }

    private FinancialHealthResponse financialHealth(MonthlyFinance latest, MonthlyFinance previous) {
        if (latest == null) {
            return new FinancialHealthResponse(0, List.of());
        }
        BigDecimal savingsComponent = component(latest.getSavingsRate(), BigDecimal.valueOf(40), BigDecimal.valueOf(35));
        BigDecimal debtToIncome = MoneyUtils.percent(latest.getEmi(), latest.getTotalIncome());
        BigDecimal debtComponent = debtToIncome.compareTo(BigDecimal.valueOf(20)) <= 0
            ? BigDecimal.valueOf(25)
            : BigDecimal.valueOf(25).subtract(component(debtToIncome.subtract(BigDecimal.valueOf(20)), BigDecimal.valueOf(40), BigDecimal.valueOf(25))).max(BigDecimal.ZERO);
        EmergencyFundResponse emergency = planningService.emergencyFund(latest.getTotalExpenses(), latest.getEmergencyFundBalance(), 6);
        BigDecimal emergencyComponent = component(emergency.progressPercentage(), MoneyUtils.ONE_HUNDRED, BigDecimal.valueOf(25));
        BigDecimal investmentComponent = investmentGrowthComponent(latest, previous);
        int score = savingsComponent.add(debtComponent).add(emergencyComponent).add(investmentComponent).setScale(0, RoundingMode.HALF_UP).intValue();
        return new FinancialHealthResponse(Math.min(100, score), List.of(
            new ScoreBreakdownItem("Savings Rate", savingsComponent, BigDecimal.valueOf(35)),
            new ScoreBreakdownItem("Debt-to-Income", debtComponent, BigDecimal.valueOf(25)),
            new ScoreBreakdownItem("Emergency Fund", emergencyComponent, BigDecimal.valueOf(25)),
            new ScoreBreakdownItem("Investment Growth", investmentComponent, BigDecimal.valueOf(15))
        ));
    }

    private BigDecimal investmentGrowthComponent(MonthlyFinance latest, MonthlyFinance previous) {
        BigDecimal latestInvestments = MonthlyFinanceService.investmentTotal(latest);
        if (previous == null) {
            return latestInvestments.compareTo(BigDecimal.ZERO) > 0 ? BigDecimal.valueOf(10) : MoneyUtils.ZERO;
        }
        BigDecimal previousInvestments = MonthlyFinanceService.investmentTotal(previous);
        if (previousInvestments.compareTo(BigDecimal.ZERO) <= 0) {
            return latestInvestments.compareTo(BigDecimal.ZERO) > 0 ? BigDecimal.valueOf(15) : MoneyUtils.ZERO;
        }
        BigDecimal growth = MoneyUtils.percent(latestInvestments.subtract(previousInvestments), previousInvestments);
        return component(growth, BigDecimal.valueOf(10), BigDecimal.valueOf(15));
    }

    private BigDecimal component(BigDecimal value, BigDecimal target, BigDecimal max) {
        return MoneyUtils.cap(MoneyUtils.money(value).multiply(max).divide(target, 2, RoundingMode.HALF_UP), max);
    }

    private List<ChartSlice> expenseBreakdown(MonthlyFinance latest) {
        if (latest == null) {
            return List.of();
        }
        return List.of(
            new ChartSlice("EMI", latest.getEmi()),
            new ChartSlice("Rent", latest.getRent()),
            new ChartSlice("Grocery", latest.getGrocery()),
            new ChartSlice("Food", latest.getFood()),
            new ChartSlice("Utilities", latest.getUtilities()),
            new ChartSlice("Fuel", latest.getFuel()),
            new ChartSlice("Entertainment", latest.getEntertainment()),
            new ChartSlice("Shopping", latest.getShopping()),
            new ChartSlice("Travel", latest.getTravel()),
            new ChartSlice("Insurance", latest.getInsurance()),
            new ChartSlice("Medical", latest.getMedical()),
            new ChartSlice("Misc", latest.getMiscellaneous())
        );
    }

    private List<ChartSlice> portfolioAllocation(MonthlyFinance latest) {
        if (latest == null) {
            return List.of();
        }
        return List.of(
            new ChartSlice("SIP", latest.getSipCurrentValue()),
            new ChartSlice("Stocks", latest.getStockCurrentValue()),
            new ChartSlice("EPF", latest.getEpfValue()),
            new ChartSlice("PPF", latest.getPpfValue()),
            new ChartSlice("NPS", latest.getNpsValue()),
            new ChartSlice("FD", latest.getFixedDepositValue()),
            new ChartSlice("Other", latest.getOtherInvestments())
        );
    }
}

