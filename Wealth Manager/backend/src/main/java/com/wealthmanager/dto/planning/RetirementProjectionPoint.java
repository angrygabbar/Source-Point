package com.wealthmanager.dto.planning;

import java.math.BigDecimal;

public record RetirementProjectionPoint(
    Integer age,
    BigDecimal projectedCorpus
) {
}

