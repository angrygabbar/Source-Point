package com.wealthmanager.service;

import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.User;
import com.wealthmanager.dto.planning.EmergencyFundResponse;
import com.wealthmanager.dto.planning.HousePurchaseRequest;
import com.wealthmanager.dto.planning.HousePurchaseResponse;
import com.wealthmanager.dto.planning.RetirementPlanRequest;
import com.wealthmanager.dto.planning.RetirementPlanResponse;
import com.wealthmanager.dto.planning.RetirementProjectionPoint;
import com.wealthmanager.exception.ApiException;
import com.wealthmanager.repository.MonthlyFinanceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
public class PlanningService {
    private final CurrentUserService currentUserService;
    private final MonthlyFinanceRepository monthlyFinanceRepository;

    @Transactional(readOnly = true)
    public EmergencyFundResponse emergencyFund(int targetMonths) {
        User user = currentUserService.getCurrentUser();
        MonthlyFinance latest = monthlyFinanceRepository.findFirstByUserOrderByMonthDesc(user).orElse(null);
        BigDecimal monthlyExpenses = latest == null ? MoneyUtils.ZERO : latest.getTotalExpenses();
        BigDecimal currentEmergencyFund = latest == null ? MoneyUtils.ZERO : latest.getEmergencyFundBalance();
        return emergencyFund(monthlyExpenses, currentEmergencyFund, targetMonths);
    }

    public EmergencyFundResponse emergencyFund(BigDecimal monthlyExpenses, BigDecimal currentEmergencyFund, int targetMonths) {
        int normalizedTarget = Math.max(6, Math.min(12, targetMonths));
        BigDecimal required = MoneyUtils.money(monthlyExpenses).multiply(BigDecimal.valueOf(normalizedTarget)).setScale(2, RoundingMode.HALF_UP);
        BigDecimal gap = MoneyUtils.subtractFloorZero(required, currentEmergencyFund);
        return new EmergencyFundResponse(
            MoneyUtils.money(monthlyExpenses),
            normalizedTarget,
            required,
            MoneyUtils.money(currentEmergencyFund),
            gap,
            MoneyUtils.percent(currentEmergencyFund, required).min(MoneyUtils.ONE_HUNDRED)
        );
    }

    public HousePurchaseResponse housePurchase(HousePurchaseRequest request) {
        BigDecimal required = MoneyUtils.money(request.propertyCost())
            .multiply(MoneyUtils.money(request.downPaymentTargetPercentage()))
            .divide(MoneyUtils.ONE_HUNDRED, 2, RoundingMode.HALF_UP);
        BigDecimal gap = MoneyUtils.subtractFloorZero(required, request.existingDownPaymentFund());
        int months = gap.compareTo(BigDecimal.ZERO) == 0
            ? 0
            : gap.divide(request.monthlyContribution(), 0, RoundingMode.CEILING).intValue();
        BigDecimal monthlyRequiredForTwelveMonths = gap.compareTo(BigDecimal.ZERO) == 0
            ? MoneyUtils.ZERO
            : gap.divide(BigDecimal.valueOf(12), 2, RoundingMode.HALF_UP);
        return new HousePurchaseResponse(
            MoneyUtils.money(request.propertyCost()),
            required,
            MoneyUtils.money(request.existingDownPaymentFund()),
            gap,
            MoneyUtils.money(request.monthlyContribution()),
            months,
            LocalDate.now().plusMonths(months),
            monthlyRequiredForTwelveMonths
        );
    }

    public RetirementPlanResponse retirementPlan(RetirementPlanRequest request) {
        if (request.retirementAge() <= request.currentAge()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Retirement age must be greater than current age");
        }

        int years = request.retirementAge() - request.currentAge();
        int months = years * 12;
        double monthlyRate = request.expectedAnnualReturn().divide(BigDecimal.valueOf(1200), 10, RoundingMode.HALF_UP).doubleValue();
        double factor = Math.pow(1 + monthlyRate, months);
        double existingFutureValue = request.existingRetirementCorpus().doubleValue() * factor;
        double sipFutureValue = monthlyRate == 0
            ? request.monthlyInvestment().doubleValue() * months
            : request.monthlyInvestment().doubleValue() * ((factor - 1) / monthlyRate);
        BigDecimal futureCorpus = MoneyUtils.money(BigDecimal.valueOf(existingFutureValue + sipFutureValue));

        BigDecimal target = MoneyUtils.money(request.targetRetirementCorpus());
        BigDecimal monthlySipNeeded = calculateMonthlySipNeeded(target, request.existingRetirementCorpus(), months, monthlyRate, factor);
        int readiness = MoneyUtils.percent(futureCorpus, target).min(MoneyUtils.ONE_HUNDRED).intValue();
        List<RetirementProjectionPoint> projections = buildRetirementProjections(request, years, monthlyRate);

        return new RetirementPlanResponse(years, futureCorpus, monthlySipNeeded, readiness, projections);
    }

    private BigDecimal calculateMonthlySipNeeded(BigDecimal target, BigDecimal existingCorpus, int months, double monthlyRate, double factor) {
        double existingFutureValue = existingCorpus.doubleValue() * factor;
        double gap = Math.max(0, target.doubleValue() - existingFutureValue);
        if (gap == 0) {
            return MoneyUtils.ZERO;
        }
        double denominator = monthlyRate == 0 ? months : (factor - 1) / monthlyRate;
        return MoneyUtils.money(BigDecimal.valueOf(gap / denominator));
    }

    private List<RetirementProjectionPoint> buildRetirementProjections(RetirementPlanRequest request, int years, double monthlyRate) {
        List<RetirementProjectionPoint> points = new ArrayList<>();
        double corpus = request.existingRetirementCorpus().doubleValue();
        for (int year = 0; year <= years; year++) {
            int age = request.currentAge() + year;
            if (year > 0) {
                for (int month = 0; month < 12; month++) {
                    corpus = corpus * (1 + monthlyRate) + request.monthlyInvestment().doubleValue();
                }
            }
            points.add(new RetirementProjectionPoint(age, MoneyUtils.money(BigDecimal.valueOf(corpus))));
        }
        return points;
    }
}

