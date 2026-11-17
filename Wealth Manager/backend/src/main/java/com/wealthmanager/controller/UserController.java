package com.wealthmanager.controller;

import com.wealthmanager.dto.user.UserProfileResponse;
import com.wealthmanager.dto.user.UserProfileUpdateRequest;
import com.wealthmanager.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @GetMapping("/me")
    public UserProfileResponse me() {
        return userService.getProfile();
    }

    @PutMapping("/me")
    public UserProfileResponse update(@Valid @RequestBody UserProfileUpdateRequest request) {
        return userService.updateProfile(request);
    }

}
