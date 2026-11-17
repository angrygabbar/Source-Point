package com.wealthmanager.controller;

import com.wealthmanager.dto.monthly.MonthlyFinanceRequest;
import com.wealthmanager.dto.monthly.MonthlyFinanceResponse;
import com.wealthmanager.service.MonthlyFinanceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/monthly-finances")
@RequiredArgsConstructor
public class MonthlyFinanceController {
    private final MonthlyFinanceService monthlyFinanceService;

    @GetMapping
    public List<MonthlyFinanceResponse> list() {
        return monthlyFinanceService.list();
    }

    @GetMapping("/{id}")
    public MonthlyFinanceResponse get(@PathVariable UUID id) {
        return monthlyFinanceService.get(id);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public MonthlyFinanceResponse create(@Valid @RequestBody MonthlyFinanceRequest request) {
        return monthlyFinanceService.create(request);
    }

    @PutMapping("/{id}")
    public MonthlyFinanceResponse update(@PathVariable UUID id, @Valid @RequestBody MonthlyFinanceRequest request) {
        return monthlyFinanceService.update(id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable UUID id) {
        monthlyFinanceService.delete(id);
    }
}

