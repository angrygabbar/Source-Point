package com.wealthmanager.service;

import com.wealthmanager.domain.User;
import com.wealthmanager.dto.user.UserProfileResponse;

public final class UserMapper {
    private UserMapper() {
    }

    public static UserProfileResponse toProfile(User user) {
        return new UserProfileResponse(
            user.getId(),
            user.getName(),
            user.getEmail(),
            user.getAge(),
            user.getMaritalStatus()
        );
    }
}

