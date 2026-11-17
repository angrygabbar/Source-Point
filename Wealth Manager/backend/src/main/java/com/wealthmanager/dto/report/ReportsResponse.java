package com.wealthmanager.dto.report;

import java.util.List;

public record ReportsResponse(
    List<MonthlyReportPoint> monthlyReports,
    List<MonthlyReportPoint> investmentReports,
    List<MonthlyReportPoint> wealthReports
) {
}

