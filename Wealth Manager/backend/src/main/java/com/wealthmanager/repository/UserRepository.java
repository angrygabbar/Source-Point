package com.wealthmanager.repository;

import com.wealthmanager.domain.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface UserRepository extends JpaRepository<User, UUID> {
    Optional<User> findByEmailIgnoreCase(String email);

    Optional<User> findBySourcePointUserId(Integer sourcePointUserId);
}

