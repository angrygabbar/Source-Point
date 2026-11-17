package com.wealthmanager.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;

@Service
public class JwtService {
    private final SecretKey key;
    private final String issuer;
    private final String audience;

    public JwtService(
        @Value("${app.sso.secret}") String secret,
        @Value("${app.sso.issuer}") String issuer,
        @Value("${app.sso.audience}") String audience
    ) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalStateException("WEALTH_MANAGER_SSO_SECRET must be configured");
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.issuer = issuer;
        this.audience = audience;
    }

    public SourcePointPrincipal parseSourcePointToken(String token) {
        Claims claims = Jwts.parser()
            .verifyWith(key)
            .requireIssuer(issuer)
            .requireAudience(audience)
            .clockSkewSeconds(30)
            .build()
            .parseSignedClaims(token)
            .getPayload();

        Object sourcePointUserIdClaim = claims.get("sourcepointUserId");
        if (!(sourcePointUserIdClaim instanceof Number sourcePointUserId)) {
            throw new IllegalArgumentException("SourcePoint user id is missing from token");
        }

        String email = claims.getSubject();
        String name = claims.get("name", String.class);
        if (email == null || email.isBlank() || name == null || name.isBlank()) {
            throw new IllegalArgumentException("SourcePoint identity is incomplete");
        }

        return new SourcePointPrincipal(sourcePointUserId.intValue(), email, name);
    }
}
