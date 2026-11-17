package com.wealthmanager.controller;

import com.wealthmanager.service.SmartInsightsService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/insights")
@RequiredArgsConstructor
public class InsightsController {
    private final SmartInsightsService smartInsightsService;

    @GetMapping
    public List<String> insights() {
        return smartInsightsService.list();
    }
}

