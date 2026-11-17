package com.wealthmanager.controller;

import com.wealthmanager.dto.report.ReportsResponse;
import com.wealthmanager.service.ReportsService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/reports")
@RequiredArgsConstructor
public class ReportsController {
    private final ReportsService reportsService;

    @GetMapping("/monthly")
    public ReportsResponse monthlyReports() {
        return reportsService.reports();
    }

    @GetMapping("/export/excel")
    public ResponseEntity<byte[]> exportExcel() {
        return ResponseEntity.ok()
            .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.attachment().filename("wealth-report.xlsx").build().toString())
            .contentType(MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
            .body(reportsService.exportExcel());
    }

    @GetMapping("/export/pdf")
    public ResponseEntity<byte[]> exportPdf() {
        return ResponseEntity.ok()
            .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.attachment().filename("wealth-report.pdf").build().toString())
            .contentType(MediaType.APPLICATION_PDF)
            .body(reportsService.exportPdf());
    }
}

