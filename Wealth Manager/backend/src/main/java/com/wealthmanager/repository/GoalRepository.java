package com.wealthmanager.repository;

import com.wealthmanager.domain.Goal;
import com.wealthmanager.domain.GoalType;
import com.wealthmanager.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface GoalRepository extends JpaRepository<Goal, UUID> {
    List<Goal> findByUserOrderByTargetDateAsc(User user);

    Optional<Goal> findFirstByUserAndGoalTypeOrderByCreatedAtDesc(User user, GoalType goalType);

    Optional<Goal> findByIdAndUser(UUID id, User user);
}

