package com.wealthmanager.repository;

import com.wealthmanager.domain.Loan;
import com.wealthmanager.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface LoanRepository extends JpaRepository<Loan, UUID> {
    List<Loan> findByUserOrderByOutstandingAmountDesc(User user);

    Optional<Loan> findByIdAndUser(UUID id, User user);
}

