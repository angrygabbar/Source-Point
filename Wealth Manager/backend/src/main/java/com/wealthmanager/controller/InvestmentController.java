package com.wealthmanager.controller;

import com.wealthmanager.dto.investment.InvestmentRequest;
import com.wealthmanager.dto.investment.InvestmentResponse;
import com.wealthmanager.service.InvestmentService;
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
@RequestMapping("/investments")
@RequiredArgsConstructor
public class InvestmentController {
    private final InvestmentService investmentService;

    @GetMapping
    public List<InvestmentResponse> list() {
        return investmentService.list();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public InvestmentResponse create(@Valid @RequestBody InvestmentRequest request) {
        return investmentService.create(request);
    }

    @PutMapping("/{id}")
    public InvestmentResponse update(@PathVariable UUID id, @Valid @RequestBody InvestmentRequest request) {
        return investmentService.update(id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable UUID id) {
        investmentService.delete(id);
    }
}

