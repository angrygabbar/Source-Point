package com.wealthmanager.service;

import com.wealthmanager.domain.Loan;
import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.User;
import com.wealthmanager.dto.loan.LoanRequest;
import com.wealthmanager.dto.loan.LoanResponse;
import com.wealthmanager.dto.loan.PrepaymentSimulationResponse;
import com.wealthmanager.exception.ApiException;
import com.wealthmanager.repository.LoanRepository;
import com.wealthmanager.repository.MonthlyFinanceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class LoanService {
    private final LoanRepository loanRepository;
    private final MonthlyFinanceRepository monthlyFinanceRepository;
    private final CurrentUserService currentUserService;

    @Transactional(readOnly = true)
    public List<LoanResponse> list() {
        User user = currentUserService.getCurrentUser();
        BigDecimal monthlyIncome = latestIncome(user);
        return loanRepository.findByUserOrderByOutstandingAmountDesc(user).stream()
            .map(loan -> toResponse(loan, monthlyIncome))
            .toList();
    }

    @Transactional
    public LoanResponse create(LoanRequest request) {
        User user = currentUserService.getCurrentUser();
        Loan loan = new Loan();
        loan.setUser(user);
        apply(loan, request);
        return toResponse(loanRepository.save(loan), latestIncome(user));
    }

    @Transactional
    public LoanResponse update(UUID id, LoanRequest request) {
        User user = currentUserService.getCurrentUser();
        Loan loan = findOwned(id, user);
        apply(loan, request);
        return toResponse(loan, latestIncome(user));
    }

    @Transactional
    public void delete(UUID id) {
        User user = currentUserService.getCurrentUser();
        loanRepository.delete(findOwned(id, user));
    }

    @Transactional(readOnly = true)
    public PrepaymentSimulationResponse simulatePrepayment(UUID id, BigDecimal prepaymentAmount) {
        User user = currentUserService.getCurrentUser();
        Loan loan = findOwned(id, user);
        if (prepaymentAmount.compareTo(loan.getOutstandingAmount()) > 0) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Prepayment cannot exceed outstanding amount");
        }
        Projection original = project(loan.getOutstandingAmount(), loan.getInterestRate(), loan.getEmi());
        BigDecimal revisedOutstanding = loan.getOutstandingAmount().subtract(prepaymentAmount).setScale(2, RoundingMode.HALF_UP);
        Projection revised = project(revisedOutstanding, loan.getInterestRate(), loan.getEmi());
        return new PrepaymentSimulationResponse(
            loan.getOutstandingAmount(),
            revisedOutstanding,
            original.months(),
            revised.months(),
            MoneyUtils.subtractFloorZero(original.totalInterest(), revised.totalInterest()),
            LocalDate.now().plusMonths(revised.months())
        );
    }

    private Loan findOwned(UUID id, User user) {
        return loanRepository.findByIdAndUser(id, user)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Loan not found"));
    }

    private LoanResponse toResponse(Loan loan, BigDecimal monthlyIncome) {
        Projection projection = project(loan.getOutstandingAmount(), loan.getInterestRate(), loan.getEmi());
        return new LoanResponse(
            loan.getId(),
            loan.getLoanName(),
            loan.getOutstandingAmount(),
            loan.getInterestRate(),
            loan.getEmi(),
            loan.getRemainingTenureMonths(),
            projection.totalInterest(),
            MoneyUtils.percent(loan.getEmi(), monthlyIncome),
            LocalDate.now().plusMonths(projection.months())
        );
    }

    private BigDecimal latestIncome(User user) {
        return monthlyFinanceRepository.findFirstByUserOrderByMonthDesc(user)
            .map(MonthlyFinance::getTotalIncome)
            .orElse(MoneyUtils.ZERO);
    }

    private void apply(Loan loan, LoanRequest request) {
        loan.setLoanName(request.loanName().trim());
        loan.setOutstandingAmount(MoneyUtils.money(request.outstandingAmount()));
        loan.setInterestRate(MoneyUtils.money(request.interestRate()));
        loan.setEmi(MoneyUtils.money(request.emi()));
        loan.setRemainingTenureMonths(request.remainingTenureMonths());
    }

    private Projection project(BigDecimal outstanding, BigDecimal annualRate, BigDecimal emi) {
        BigDecimal balance = MoneyUtils.money(outstanding);
        if (balance.compareTo(BigDecimal.ZERO) == 0) {
            return new Projection(0, MoneyUtils.ZERO);
        }
        BigDecimal monthlyRate = annualRate.divide(BigDecimal.valueOf(1200), 12, RoundingMode.HALF_UP);
        BigDecimal totalInterest = MoneyUtils.ZERO;
        int months = 0;
        while (balance.compareTo(BigDecimal.ZERO) > 0 && months < 1200) {
            BigDecimal interest = balance.multiply(monthlyRate).setScale(2, RoundingMode.HALF_UP);
            BigDecimal principal = emi.subtract(interest);
            if (principal.compareTo(BigDecimal.ZERO) <= 0) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "EMI is too low to amortize the loan");
            }
            totalInterest = totalInterest.add(interest).setScale(2, RoundingMode.HALF_UP);
            balance = balance.subtract(principal).setScale(2, RoundingMode.HALF_UP);
            months++;
        }
        return new Projection(months, totalInterest);
    }

    private record Projection(int months, BigDecimal totalInterest) {
    }
}

