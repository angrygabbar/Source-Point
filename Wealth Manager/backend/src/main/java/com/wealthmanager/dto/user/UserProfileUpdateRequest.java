package com.wealthmanager.dto.user;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record UserProfileUpdateRequest(
    @NotBlank @Size(max = 120) String name,
    @NotNull @Min(18) Integer age,
    @NotBlank @Size(max = 40) String maritalStatus
) {
}

