package com.wealthmanager.controller;

import com.wealthmanager.dto.dashboard.DashboardResponse;
import com.wealthmanager.service.DashboardService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/dashboard")
@RequiredArgsConstructor
public class DashboardController {
    private final DashboardService dashboardService;

    @GetMapping
    public DashboardResponse dashboard() {
        return dashboardService.dashboard();
    }
}

