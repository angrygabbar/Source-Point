package com.wealthmanager.service;

import com.wealthmanager.domain.Goal;
import com.wealthmanager.domain.User;
import com.wealthmanager.dto.goal.GoalRequest;
import com.wealthmanager.dto.goal.GoalResponse;
import com.wealthmanager.exception.ApiException;
import com.wealthmanager.repository.GoalRepository;
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
public class GoalService {
    private final GoalRepository goalRepository;
    private final CurrentUserService currentUserService;

    @Transactional(readOnly = true)
    public List<GoalResponse> list() {
        User user = currentUserService.getCurrentUser();
        return goalRepository.findByUserOrderByTargetDateAsc(user).stream().map(this::toResponse).toList();
    }

    @Transactional
    public GoalResponse create(GoalRequest request) {
        User user = currentUserService.getCurrentUser();
        Goal goal = new Goal();
        goal.setUser(user);
        apply(goal, request);
        return toResponse(goalRepository.save(goal));
    }

    @Transactional
    public GoalResponse update(UUID id, GoalRequest request) {
        User user = currentUserService.getCurrentUser();
        Goal goal = findOwned(id, user);
        apply(goal, request);
        return toResponse(goal);
    }

    @Transactional
    public void delete(UUID id) {
        User user = currentUserService.getCurrentUser();
        goalRepository.delete(findOwned(id, user));
    }

    public GoalResponse toResponse(Goal goal) {
        BigDecimal progress = MoneyUtils.percent(goal.getCurrentAmount(), goal.getTargetAmount()).min(MoneyUtils.ONE_HUNDRED);
        BigDecimal remaining = MoneyUtils.subtractFloorZero(goal.getTargetAmount(), goal.getCurrentAmount());
        LocalDate estimatedCompletion = estimateCompletionDate(remaining, goal.getMonthlyContribution());
        return new GoalResponse(
            goal.getId(),
            goal.getGoalType(),
            goal.getGoalName(),
            goal.getTargetAmount(),
            goal.getCurrentAmount(),
            goal.getTargetDate(),
            goal.getMonthlyContribution(),
            progress,
            remaining,
            estimatedCompletion
        );
    }

    private Goal findOwned(UUID id, User user) {
        return goalRepository.findByIdAndUser(id, user)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Goal not found"));
    }

    private void apply(Goal goal, GoalRequest request) {
        if (request.currentAmount().compareTo(request.targetAmount()) > 0) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Current amount cannot exceed target amount");
        }
        goal.setGoalType(request.goalType());
        goal.setGoalName(request.goalName().trim());
        goal.setTargetAmount(MoneyUtils.money(request.targetAmount()));
        goal.setCurrentAmount(MoneyUtils.money(request.currentAmount()));
        goal.setTargetDate(request.targetDate());
        goal.setMonthlyContribution(MoneyUtils.money(request.monthlyContribution()));
    }

    private LocalDate estimateCompletionDate(BigDecimal remaining, BigDecimal monthlyContribution) {
        if (remaining.compareTo(BigDecimal.ZERO) <= 0) {
            return LocalDate.now();
        }
        if (monthlyContribution == null || monthlyContribution.compareTo(BigDecimal.ZERO) <= 0) {
            return null;
        }
        int months = remaining.divide(monthlyContribution, 0, RoundingMode.CEILING).intValue();
        return LocalDate.now().plusMonths(months);
    }
}

