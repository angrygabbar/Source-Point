package com.wealthmanager.service;

import com.lowagie.text.Document;
import com.lowagie.text.DocumentException;
import com.lowagie.text.Paragraph;
import com.lowagie.text.pdf.PdfPTable;
import com.lowagie.text.pdf.PdfWriter;
import com.wealthmanager.domain.MonthlyFinance;
import com.wealthmanager.domain.ReportSnapshot;
import com.wealthmanager.domain.User;
import com.wealthmanager.dto.report.MonthlyReportPoint;
import com.wealthmanager.dto.report.ReportsResponse;
import com.wealthmanager.repository.MonthlyFinanceRepository;
import com.wealthmanager.repository.ReportSnapshotRepository;
import lombok.RequiredArgsConstructor;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.math.BigDecimal;
import java.util.Comparator;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ReportsService {
    private final CurrentUserService currentUserService;
    private final MonthlyFinanceRepository monthlyFinanceRepository;
    private final ReportSnapshotRepository reportSnapshotRepository;

    @Transactional(readOnly = true)
    public ReportsResponse reports() {
        List<MonthlyReportPoint> points = pointsFor(currentUserService.getCurrentUser());
        return new ReportsResponse(points, points, points);
    }

    @Transactional(readOnly = true)
    public byte[] exportExcel() {
        List<MonthlyReportPoint> points = pointsFor(currentUserService.getCurrentUser());
        try (Workbook workbook = new XSSFWorkbook(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            Sheet sheet = workbook.createSheet("Monthly Reports");
            Row header = sheet.createRow(0);
            List<String> headers = List.of("Month", "Income", "Expenses", "Savings", "Investments", "Net Worth");
            for (int i = 0; i < headers.size(); i++) {
                header.createCell(i).setCellValue(headers.get(i));
            }
            for (int rowIndex = 0; rowIndex < points.size(); rowIndex++) {
                MonthlyReportPoint point = points.get(rowIndex);
                Row row = sheet.createRow(rowIndex + 1);
                row.createCell(0).setCellValue(point.month().toString());
                writeMoney(row, 1, point.income());
                writeMoney(row, 2, point.expenses());
                writeMoney(row, 3, point.savings());
                writeMoney(row, 4, point.investments());
                writeMoney(row, 5, point.netWorth());
            }
            for (int i = 0; i < headers.size(); i++) {
                sheet.autoSizeColumn(i);
            }
            workbook.write(out);
            return out.toByteArray();
        } catch (IOException exception) {
            throw new IllegalStateException("Unable to export Excel report", exception);
        }
    }

    @Transactional(readOnly = true)
    public byte[] exportPdf() {
        List<MonthlyReportPoint> points = pointsFor(currentUserService.getCurrentUser());
        try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            Document document = new Document();
            PdfWriter.getInstance(document, out);
            document.open();
            document.add(new Paragraph("Personal Finance Monthly Report"));
            document.add(new Paragraph(" "));
            PdfPTable table = new PdfPTable(6);
            List.of("Month", "Income", "Expenses", "Savings", "Investments", "Net Worth")
                .forEach(table::addCell);
            for (MonthlyReportPoint point : points) {
                table.addCell(point.month().toString());
                table.addCell(point.income().toPlainString());
                table.addCell(point.expenses().toPlainString());
                table.addCell(point.savings().toPlainString());
                table.addCell(point.investments().toPlainString());
                table.addCell(point.netWorth().toPlainString());
            }
            document.add(table);
            document.close();
            return out.toByteArray();
        } catch (DocumentException | IOException exception) {
            throw new IllegalStateException("Unable to export PDF report", exception);
        }
    }

    private List<MonthlyReportPoint> pointsFor(User user) {
        List<ReportSnapshot> snapshots = reportSnapshotRepository.findByUserOrderByMonthAsc(user);
        if (!snapshots.isEmpty()) {
            return snapshots.stream()
                .map(snapshot -> new MonthlyReportPoint(
                    snapshot.getMonth(),
                    snapshot.getIncomeTotal(),
                    snapshot.getExpenseTotal(),
                    snapshot.getSavingsTotal(),
                    snapshot.getInvestmentTotal(),
                    snapshot.getNetWorth()
                ))
                .toList();
        }
        return monthlyFinanceRepository.findByUserOrderByMonthDesc(user).stream()
            .sorted(Comparator.comparing(MonthlyFinance::getMonth))
            .map(finance -> new MonthlyReportPoint(
                finance.getMonth(),
                finance.getTotalIncome(),
                finance.getTotalExpenses(),
                finance.getTotalSavings(),
                MonthlyFinanceService.investmentTotal(finance),
                finance.getNetWorth()
            ))
            .toList();
    }

    private void writeMoney(Row row, int column, BigDecimal value) {
        row.createCell(column).setCellValue(value.doubleValue());
    }
}
