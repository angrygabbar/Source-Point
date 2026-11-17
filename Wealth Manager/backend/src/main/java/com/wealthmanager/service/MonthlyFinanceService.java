package com.wealthmanager.service;

import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.User;
import com.wealthmanager.dto.monthly.MonthlyFinanceRequest;
import com.wealthmanager.dto.monthly.MonthlyFinanceResponse;
import com.wealthmanager.exception.ApiException;
import com.wealthmanager.repository.MonthlyFinanceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class MonthlyFinanceService {
    private final MonthlyFinanceRepository monthlyFinanceRepository;
    private final CurrentUserService currentUserService;
    private final ReportSnapshotService reportSnapshotService;

    @Transactional(readOnly = true)
    public List<MonthlyFinanceResponse> list() {
        User user = currentUserService.getCurrentUser();
        return monthlyFinanceRepository.findByUserOrderByMonthDesc(user).stream()
            .map(MonthlyFinanceService::toResponse)
            .toList();
    }

    @Transactional(readOnly = true)
    public MonthlyFinanceResponse get(UUID id) {
        User user = currentUserService.getCurrentUser();
        return toResponse(findOwned(id, user));
    }

    @Transactional
    public MonthlyFinanceResponse create(MonthlyFinanceRequest request) {
        User user = currentUserService.getCurrentUser();
        LocalDate month = normalizeMonth(request.month());
        if (monthlyFinanceRepository.existsByUserAndMonth(user, month)) {
            throw new ApiException(HttpStatus.CONFLICT, "A monthly finance record already exists for " + month);
        }
        MonthlyFinance finance = new MonthlyFinance();
        finance.setUser(user);
        applyRequest(finance, request, month);
        MonthlyFinance saved = monthlyFinanceRepository.save(finance);
        reportSnapshotService.refreshSnapshot(user, saved);
        return toResponse(saved);
    }

    @Transactional
    public MonthlyFinanceResponse update(UUID id, MonthlyFinanceRequest request) {
        User user = currentUserService.getCurrentUser();
        MonthlyFinance finance = findOwned(id, user);
        LocalDate month = normalizeMonth(request.month());
        if (monthlyFinanceRepository.existsByUserAndMonthAndIdNot(user, month, id)) {
            throw new ApiException(HttpStatus.CONFLICT, "A monthly finance record already exists for " + month);
        }
        applyRequest(finance, request, month);
        reportSnapshotService.refreshSnapshot(user, finance);
        return toResponse(finance);
    }

    @Transactional
    public void delete(UUID id) {
        User user = currentUserService.getCurrentUser();
        monthlyFinanceRepository.delete(findOwned(id, user));
    }

    private MonthlyFinance findOwned(UUID id, User user) {
        return monthlyFinanceRepository.findByIdAndUser(id, user)
            .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Monthly finance record not found"));
    }

    private static LocalDate normalizeMonth(LocalDate date) {
        return date.withDayOfMonth(1);
    }

    private static void applyRequest(MonthlyFinance finance, MonthlyFinanceRequest request, LocalDate month) {
        finance.setMonth(month);
        finance.setSalary(MoneyUtils.money(request.salary()));
        finance.setBonus(MoneyUtils.money(request.bonus()));
        finance.setFreelanceIncome(MoneyUtils.money(request.freelanceIncome()));
        finance.setOtherIncome(MoneyUtils.money(request.otherIncome()));
        finance.setEmi(MoneyUtils.money(request.emi()));
        finance.setRent(MoneyUtils.money(request.rent()));
        finance.setGrocery(MoneyUtils.money(request.grocery()));
        finance.setFood(MoneyUtils.money(request.food()));
        finance.setUtilities(MoneyUtils.money(request.utilities()));
        finance.setFuel(MoneyUtils.money(request.fuel()));
        finance.setEntertainment(MoneyUtils.money(request.entertainment()));
        finance.setShopping(MoneyUtils.money(request.shopping()));
        finance.setTravel(MoneyUtils.money(request.travel()));
        finance.setInsurance(MoneyUtils.money(request.insurance()));
        finance.setMedical(MoneyUtils.money(request.medical()));
        finance.setMiscellaneous(MoneyUtils.money(request.miscellaneous()));
        finance.setSipMonthlyContribution(MoneyUtils.money(request.sipMonthlyContribution()));
        finance.setSipCurrentValue(MoneyUtils.money(request.sipCurrentValue()));
        finance.setStockInvestmentAmount(MoneyUtils.money(request.stockInvestmentAmount()));
        finance.setStockCurrentValue(MoneyUtils.money(request.stockCurrentValue()));
        finance.setEpfValue(MoneyUtils.money(request.epfValue()));
        finance.setPpfValue(MoneyUtils.money(request.ppfValue()));
        finance.setNpsValue(MoneyUtils.money(request.npsValue()));
        finance.setFixedDepositValue(MoneyUtils.money(request.fixedDepositValue()));
        finance.setOtherInvestments(MoneyUtils.money(request.otherInvestments()));
        finance.setSavingsAccountBalance(MoneyUtils.money(request.savingsAccountBalance()));
        finance.setEmergencyFundBalance(MoneyUtils.money(request.emergencyFundBalance()));
        finance.setHouseFundBalance(MoneyUtils.money(request.houseFundBalance()));
        finance.setHomeLoan(MoneyUtils.money(request.homeLoan()));
        finance.setPersonalLoan(MoneyUtils.money(request.personalLoan()));
        finance.setVehicleLoan(MoneyUtils.money(request.vehicleLoan()));
        finance.setCreditCardOutstanding(MoneyUtils.money(request.creditCardOutstanding()));
        finance.setOtherLoan(MoneyUtils.money(request.otherLoan()));

        finance.setTotalIncome(incomeTotal(finance));
        finance.setTotalExpenses(expenseTotal(finance));
        finance.setTotalSavings(finance.getTotalIncome().subtract(finance.getTotalExpenses()).setScale(2, java.math.RoundingMode.HALF_UP));
        finance.setSavingsRate(MoneyUtils.percent(finance.getTotalSavings(), finance.getTotalIncome()));
        finance.setNetWorth(assetTotal(finance).add(investmentTotal(finance)).subtract(liabilityTotal(finance)).setScale(2, java.math.RoundingMode.HALF_UP));
    }

    public static BigDecimal incomeTotal(MonthlyFinance finance) {
        return MoneyUtils.sum(List.of(finance.getSalary(), finance.getBonus(), finance.getFreelanceIncome(), finance.getOtherIncome()));
    }

    public static BigDecimal expenseTotal(MonthlyFinance finance) {
        return MoneyUtils.sum(List.of(
            finance.getEmi(),
            finance.getRent(),
            finance.getGrocery(),
            finance.getFood(),
            finance.getUtilities(),
            finance.getFuel(),
            finance.getEntertainment(),
            finance.getShopping(),
            finance.getTravel(),
            finance.getInsurance(),
            finance.getMedical(),
            finance.getMiscellaneous()
        ));
    }

    public static BigDecimal investmentTotal(MonthlyFinance finance) {
        return MoneyUtils.sum(List.of(
            finance.getSipCurrentValue(),
            finance.getStockCurrentValue(),
            finance.getEpfValue(),
            finance.getPpfValue(),
            finance.getNpsValue(),
            finance.getFixedDepositValue(),
            finance.getOtherInvestments()
        ));
    }

    public static BigDecimal assetTotal(MonthlyFinance finance) {
        return MoneyUtils.sum(List.of(
            finance.getSavingsAccountBalance(),
            finance.getEmergencyFundBalance(),
            finance.getHouseFundBalance()
        ));
    }

    public static BigDecimal liabilityTotal(MonthlyFinance finance) {
        return MoneyUtils.sum(List.of(
            finance.getHomeLoan(),
            finance.getPersonalLoan(),
            finance.getVehicleLoan(),
            finance.getCreditCardOutstanding(),
            finance.getOtherLoan()
        ));
    }

    public static MonthlyFinanceResponse toResponse(MonthlyFinance finance) {
        return new MonthlyFinanceResponse(
            finance.getId(),
            finance.getMonth(),
            finance.getSalary(),
            finance.getBonus(),
            finance.getFreelanceIncome(),
            finance.getOtherIncome(),
            finance.getEmi(),
            finance.getRent(),
            finance.getGrocery(),
            finance.getFood(),
            finance.getUtilities(),
            finance.getFuel(),
            finance.getEntertainment(),
            finance.getShopping(),
            finance.getTravel(),
            finance.getInsurance(),
            finance.getMedical(),
            finance.getMiscellaneous(),
            finance.getSipMonthlyContribution(),
            finance.getSipCurrentValue(),
            finance.getStockInvestmentAmount(),
            finance.getStockCurrentValue(),
            finance.getEpfValue(),
            finance.getPpfValue(),
            finance.getNpsValue(),
            finance.getFixedDepositValue(),
            finance.getOtherInvestments(),
            finance.getSavingsAccountBalance(),
            finance.getEmergencyFundBalance(),
            finance.getHouseFundBalance(),
            finance.getHomeLoan(),
            finance.getPersonalLoan(),
            finance.getVehicleLoan(),
            finance.getCreditCardOutstanding(),
            finance.getOtherLoan(),
            finance.getTotalIncome(),
            finance.getTotalExpenses(),
            finance.getTotalSavings(),
            finance.getSavingsRate(),
            finance.getNetWorth()
        );
    }
}

