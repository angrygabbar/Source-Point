package com.wealthmanager.dto.planning;

import java.math.BigDecimal;
import java.util.List;

public record RetirementPlanResponse(
    Integer yearsToRetirement,
    BigDecimal futureCorpus,
    BigDecimal monthlySipNeeded,
    Integer retirementReadinessScore,
    List<RetirementProjectionPoint> projections
) {
}

