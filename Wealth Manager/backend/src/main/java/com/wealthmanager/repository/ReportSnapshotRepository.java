package com.wealthmanager.repository;

import com.wealthmanager.domain.ReportSnapshot;
import com.wealthmanager.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ReportSnapshotRepository extends JpaRepository<ReportSnapshot, UUID> {
    List<ReportSnapshot> findByUserOrderByMonthAsc(User user);

    Optional<ReportSnapshot> findByUserAndMonth(User user, LocalDate month);
}

