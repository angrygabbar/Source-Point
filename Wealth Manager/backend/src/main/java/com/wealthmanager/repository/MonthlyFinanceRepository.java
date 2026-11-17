package com.wealthmanager.repository;

import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface MonthlyFinanceRepository extends JpaRepository<MonthlyFinance, UUID> {
    boolean existsByUserAndMonth(User user, LocalDate month);

    boolean existsByUserAndMonthAndIdNot(User user, LocalDate month, UUID id);

    List<MonthlyFinance> findByUserOrderByMonthDesc(User user);

    List<MonthlyFinance> findTop12ByUserOrderByMonthDesc(User user);

    Optional<MonthlyFinance> findFirstByUserOrderByMonthDesc(User user);

    Optional<MonthlyFinance> findByUserAndMonth(User user, LocalDate month);

    Optional<MonthlyFinance> findByIdAndUser(UUID id, User user);
}

