package com.wealthmanager.dto.error;

import java.time.Instant;
import java.util.List;

public record ApiErrorResponse(
    Instant timestamp,
    int status,
    String error,
    List<String> details
) {
}

