package com.wealthmanager.service;

import com.wealthmanager.domain.BudgetCategory;
import com.wealthmanager.domain.BudgetStatus;
import com.wealthmanager.domain.MonthlyBudget;
import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.User;
import com.wealthmanager.dto.budget.BudgetRequest;
import com.wealthmanager.dto.budget.BudgetResponse;
import com.wealthmanager.dto.budget.BudgetSummaryResponse;
import com.wealthmanager.exception.ApiException;
import com.wealthmanager.repository.MonthlyBudgetRepository;
import com.wealthmanager.repository.MonthlyFinanceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class BudgetService {
    private final MonthlyBudgetRepository monthlyBudgetRepository;
    private final MonthlyFinanceRepository monthlyFinanceRepository;
    private final CurrentUserService currentUserService;

    @Transactional(readOnly = true)
    public BudgetSummaryResponse summary(LocalDate requestedMonth) {
        User user = currentUserService.getCurrentUser();
        return summaryForUser(user, requestedMonth);
    }

    public BudgetSummaryResponse summaryForUser(User user, LocalDate requestedMonth) {
        LocalDate month = normalizeMonth(requestedMonth == null ? LocalDate.now() : requestedMonth);
        MonthlyFinance finance = monthlyFinanceRepository.findByUserAndMonth(user, month).orElse(null);
        List<BudgetResponse> budgets = monthlyBudgetRepository.findByUserAndMonthOrderByCategoryAsc(user, month).stream()
            .map(budget -> toResponse(budget, finance))
            .toList();
        BigDecimal totalBudget = budgets.stream()
            .map(BudgetResponse::limitAmount)
            .reduce(MoneyUtils.ZERO, BigDecimal::add);
        BigDecimal totalSpent = budgets.stream()
            .map(BudgetResponse::spentAmount)
            .reduce(MoneyUtils.ZERO, BigDecimal::add);
        return new BudgetSummaryResponse(
            month,
            MoneyUtils.money(totalBudget),
            MoneyUtils.money(totalSpent),
            MoneyUtils.subtractFloorZero(totalBudget, totalSpent),
            MoneyUtils.percent(totalSpent, totalBudget),
            budgets.stream().filter(item -> item.status() == BudgetStatus.WARNING).count(),
            budgets.stream().filter(item -> item.status() == BudgetStatus.OVER_BUDGET).count(),
            budgets
        );
    }

    @Transactional
    public BudgetResponse create(BudgetRequest request) {
        User user = currentUserService.getCurrentUser();
        LocalDate month = normalizeMonth(request.month());
        if (monthlyBudgetRepository.existsByUserAndMonthAndCategory(user, month, request.category())) {
            throw new ApiException(HttpStatus.CONFLICT, "A budget already exists for this month and category");
        }
        MonthlyBudget budget = new MonthlyBudget();
        budget.setUser(user);
        apply(budget, request, month);
        MonthlyBudget saved = monthlyBudgetRepository.save(budget);
        MonthlyFinance finance = monthlyFinanceRepository.findByUserAndMonth(user, month).orElse(null);
        return toResponse(saved, finance);
    }

    @Transactional
    public BudgetResponse update(UUID id, BudgetRequest request) {
        User user = currentUserService.getCurrentUser();
        MonthlyBudget budget = findOwned(id, user);
        LocalDate month = normalizeMonth(request.month());
        if (monthlyBudgetRepository.existsByUserAndMonthAndCategoryAndIdNot(user, month, request.category(), id)) {
            throw new ApiException(HttpStatus.CONFLICT, "A budget already exists for this month and category");
        }
        apply(budget, request, month);
        MonthlyFinance finance = monthlyFinanceRepository.findByUserAndMonth(user, month).orElse(null);
        return toResponse(budget, finance);
    }

    @Transactional
    public void delete(UUID id) {
        User user = currentUserService.getCurrentUser();
        monthlyBudgetRepository.delete(findOwned(id, user));
    }

    private MonthlyBudget findOwned(UUID id, User user) {
        return monthlyBudgetRepository.findByIdAndUser(id, user)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Budget not found"));
    }

    private void apply(MonthlyBudget budget, BudgetRequest request, LocalDate month) {
        budget.setMonth(month);
        budget.setCategory(request.category());
        budget.setLimitAmount(MoneyUtils.money(request.limitAmount()));
        budget.setAlertThresholdPercentage(MoneyUtils.money(request.alertThresholdPercentage()));
        budget.setNotes(request.notes() == null || request.notes().isBlank() ? null : request.notes().trim());
    }

    private BudgetResponse toResponse(MonthlyBudget budget, MonthlyFinance finance) {
        BigDecimal spent = spentFor(budget.getCategory(), finance);
        BigDecimal utilization = MoneyUtils.percent(spent, budget.getLimitAmount());
        BudgetStatus status = utilization.compareTo(BigDecimal.valueOf(100)) > 0
            ? BudgetStatus.OVER_BUDGET
            : utilization.compareTo(budget.getAlertThresholdPercentage()) >= 0
                ? BudgetStatus.WARNING
                : BudgetStatus.ON_TRACK;
        return new BudgetResponse(
            budget.getId(),
            budget.getMonth(),
            budget.getCategory(),
            budget.getLimitAmount(),
            budget.getAlertThresholdPercentage(),
            budget.getNotes(),
            spent,
            MoneyUtils.subtractFloorZero(budget.getLimitAmount(), spent),
            utilization.setScale(2, RoundingMode.HALF_UP),
            status
        );
    }

    private BigDecimal spentFor(BudgetCategory category, MonthlyFinance finance) {
        if (finance == null) {
            return MoneyUtils.ZERO;
        }
        return switch (category) {
            case EMI -> finance.getEmi();
            case RENT -> finance.getRent();
            case GROCERY -> finance.getGrocery();
            case FOOD -> finance.getFood();
            case UTILITIES -> finance.getUtilities();
            case FUEL -> finance.getFuel();
            case ENTERTAINMENT -> finance.getEntertainment();
            case SHOPPING -> finance.getShopping();
            case TRAVEL -> finance.getTravel();
            case INSURANCE -> finance.getInsurance();
            case MEDICAL -> finance.getMedical();
            case MISCELLANEOUS -> finance.getMiscellaneous();
        };
    }

    private LocalDate normalizeMonth(LocalDate month) {
        return month.withDayOfMonth(1);
    }
}
