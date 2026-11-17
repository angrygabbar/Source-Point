package com.wealthmanager.repository;

import com.wealthmanager.domain.Investment;
import com.wealthmanager.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface InvestmentRepository extends JpaRepository<Investment, UUID> {
    List<Investment> findByUserOrderByInvestmentTypeAscInvestmentNameAsc(User user);

    Optional<Investment> findByIdAndUser(UUID id, User user);
}

