package com.wealthmanager.service;

import com.wealthmanager.domain.Investment;
import com.wealthmanager.domain.User;
import com.wealthmanager.dto.investment.InvestmentRequest;
import com.wealthmanager.dto.investment.InvestmentResponse;
import com.wealthmanager.exception.ApiException;
import com.wealthmanager.repository.InvestmentRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class InvestmentService {
    private final InvestmentRepository investmentRepository;
    private final CurrentUserService currentUserService;

    @Transactional(readOnly = true)
    public List<InvestmentResponse> list() {
        User user = currentUserService.getCurrentUser();
        return investmentRepository.findByUserOrderByInvestmentTypeAscInvestmentNameAsc(user).stream()
            .map(InvestmentService::toResponse)
            .toList();
    }

    @Transactional
    public InvestmentResponse create(InvestmentRequest request) {
        User user = currentUserService.getCurrentUser();
        Investment investment = new Investment();
        investment.setUser(user);
        apply(investment, request);
        return toResponse(investmentRepository.save(investment));
    }

    @Transactional
    public InvestmentResponse update(UUID id, InvestmentRequest request) {
        User user = currentUserService.getCurrentUser();
        Investment investment = findOwned(id, user);
        apply(investment, request);
        return toResponse(investment);
    }

    @Transactional
    public void delete(UUID id) {
        User user = currentUserService.getCurrentUser();
        investmentRepository.delete(findOwned(id, user));
    }

    public static InvestmentResponse toResponse(Investment investment) {
        BigDecimal returnsAmount = investment.getCurrentValue().subtract(investment.getInvestedAmount()).setScale(2, java.math.RoundingMode.HALF_UP);
        return new InvestmentResponse(
            investment.getId(),
            investment.getInvestmentType(),
            investment.getInvestmentName(),
            investment.getInvestedAmount(),
            investment.getCurrentValue(),
            investment.getQuantity(),
            investment.getAveragePrice(),
            returnsAmount,
            MoneyUtils.percent(returnsAmount, investment.getInvestedAmount())
        );
    }

    private Investment findOwned(UUID id, User user) {
        return investmentRepository.findByIdAndUser(id, user)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Investment not found"));
    }

    private void apply(Investment investment, InvestmentRequest request) {
        investment.setInvestmentType(request.investmentType());
        investment.setInvestmentName(request.investmentName().trim());
        investment.setInvestedAmount(MoneyUtils.money(request.investedAmount()));
        investment.setCurrentValue(MoneyUtils.money(request.currentValue()));
        investment.setQuantity(request.quantity());
        investment.setAveragePrice(request.averagePrice() == null ? null : MoneyUtils.money(request.averagePrice()));
    }
}

