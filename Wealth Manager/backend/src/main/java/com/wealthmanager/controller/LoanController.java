package com.wealthmanager.controller;

import com.wealthmanager.dto.loan.LoanRequest;
import com.wealthmanager.dto.loan.LoanResponse;
import com.wealthmanager.dto.loan.PrepaymentSimulationRequest;
import com.wealthmanager.dto.loan.PrepaymentSimulationResponse;
import com.wealthmanager.service.LoanService;
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
@RequestMapping("/loans")
@RequiredArgsConstructor
public class LoanController {
    private final LoanService loanService;

    @GetMapping
    public List<LoanResponse> list() {
        return loanService.list();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public LoanResponse create(@Valid @RequestBody LoanRequest request) {
        return loanService.create(request);
    }

    @PutMapping("/{id}")
    public LoanResponse update(@PathVariable UUID id, @Valid @RequestBody LoanRequest request) {
        return loanService.update(id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable UUID id) {
        loanService.delete(id);
    }

    @PostMapping("/{id}/simulate-prepayment")
    public PrepaymentSimulationResponse simulatePrepayment(
        @PathVariable UUID id,
        @Valid @RequestBody PrepaymentSimulationRequest request
    ) {
        return loanService.simulatePrepayment(id, request.prepaymentAmount());
    }
}

