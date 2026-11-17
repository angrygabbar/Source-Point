package com.wealthmanager.dto.user;

import java.util.UUID;

public record UserProfileResponse(
    UUID id,
    String name,
    String email,
    Integer age,
    String maritalStatus
) {
}

