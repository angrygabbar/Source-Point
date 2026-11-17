package com.wealthmanager.service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Collection;

public final class MoneyUtils {
    public static final BigDecimal ZERO = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
    public static final BigDecimal ONE_HUNDRED = BigDecimal.valueOf(100).setScale(2, RoundingMode.HALF_UP);

    private MoneyUtils() {
    }

    public static BigDecimal money(BigDecimal value) {
        return value == null ? ZERO : value.setScale(2, RoundingMode.HALF_UP);
    }

    public static BigDecimal percent(BigDecimal numerator, BigDecimal denominator) {
        if (denominator == null || denominator.compareTo(BigDecimal.ZERO) <= 0) {
            return ZERO;
        }
        return money(numerator).multiply(ONE_HUNDRED).divide(money(denominator), 2, RoundingMode.HALF_UP);
    }

    public static BigDecimal cap(BigDecimal value, BigDecimal max) {
        BigDecimal normalized = money(value);
        if (normalized.compareTo(BigDecimal.ZERO) < 0) {
            return ZERO;
        }
        return normalized.min(max);
    }

    public static BigDecimal sum(Collection<BigDecimal> values) {
        return values.stream().map(MoneyUtils::money).reduce(ZERO, BigDecimal::add).setScale(2, RoundingMode.HALF_UP);
    }

    public static BigDecimal subtractFloorZero(BigDecimal left, BigDecimal right) {
        BigDecimal result = money(left).subtract(money(right));
        return result.compareTo(BigDecimal.ZERO) < 0 ? ZERO : money(result);
    }
}

