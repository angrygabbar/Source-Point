package com.wealthmanager.service;

import com.wealthmanager.domain.User;
import com.wealthmanager.dto.user.UserProfileResponse;
import com.wealthmanager.dto.user.UserProfileUpdateRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class UserService {
    private final CurrentUserService currentUserService;

    @Transactional(readOnly = true)
    public UserProfileResponse getProfile() {
        return UserMapper.toProfile(currentUserService.getCurrentUser());
    }

    @Transactional
    public UserProfileResponse updateProfile(UserProfileUpdateRequest request) {
        User user = currentUserService.getCurrentUser();
        user.setName(request.name().trim());
        user.setAge(request.age());
        user.setMaritalStatus(request.maritalStatus().trim());
        return UserMapper.toProfile(user);
    }
}

