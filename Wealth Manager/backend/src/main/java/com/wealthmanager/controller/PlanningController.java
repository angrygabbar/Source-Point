package com.wealthmanager.controller;

import com.wealthmanager.dto.planning.EmergencyFundResponse;
import com.wealthmanager.dto.planning.HousePurchaseRequest;
import com.wealthmanager.dto.planning.HousePurchaseResponse;
import com.wealthmanager.dto.planning.RetirementPlanRequest;
import com.wealthmanager.dto.planning.RetirementPlanResponse;
import com.wealthmanager.service.PlanningService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/planning")
@RequiredArgsConstructor
public class PlanningController {
    private final PlanningService planningService;

    @GetMapping("/emergency-fund")
    public EmergencyFundResponse emergencyFund(@RequestParam(defaultValue = "6") int targetMonths) {
        return planningService.emergencyFund(targetMonths);
    }

    @PostMapping("/house-purchase")
    public HousePurchaseResponse housePurchase(@Valid @RequestBody HousePurchaseRequest request) {
        return planningService.housePurchase(request);
    }

    @PostMapping("/retirement")
    public RetirementPlanResponse retirement(@Valid @RequestBody RetirementPlanRequest request) {
        return planningService.retirementPlan(request);
    }
}

