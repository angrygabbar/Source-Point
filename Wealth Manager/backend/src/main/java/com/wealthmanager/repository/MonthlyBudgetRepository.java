package com.wealthmanager.repository;

import com.wealthmanager.domain.BudgetCategory;
import com.wealthmanager.domain.MonthlyBudget;
import com.wealthmanager.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface MonthlyBudgetRepository extends JpaRepository<MonthlyBudget, UUID> {
    List<MonthlyBudget> findByUserAndMonthOrderByCategoryAsc(User user, LocalDate month);

    Optional<MonthlyBudget> findByIdAndUser(UUID id, User user);

    boolean existsByUserAndMonthAndCategory(User user, LocalDate month, BudgetCategory category);

    boolean existsByUserAndMonthAndCategoryAndIdNot(User user, LocalDate month, BudgetCategory category, UUID id);
}

