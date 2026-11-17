package com.wealthmanager.service;

import com.wealthmanager.domain.User;
import com.wealthmanager.exception.ApiException;
import com.wealthmanager.repository.UserRepository;
import com.wealthmanager.security.SourcePointPrincipal;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.Locale;

@Service
@RequiredArgsConstructor
public class CurrentUserService {
    private static final String UNSPECIFIED_MARITAL_STATUS = "Not specified";

    private final UserRepository userRepository;

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public User ensureLinkedUser(SourcePointPrincipal identity) {
        User user = userRepository.findBySourcePointUserId(identity.sourcePointUserId()).orElse(null);
        boolean changed = false;
        if (user == null) {
            user = userRepository.findByEmailIgnoreCase(identity.email()).orElse(null);
            if (user != null && user.getSourcePointUserId() != null
                && !user.getSourcePointUserId().equals(identity.sourcePointUserId())) {
                throw new ApiException(HttpStatus.CONFLICT, "This finance profile is linked to another SourcePoint account");
            }
            if (user == null) {
                user = User.builder()
                    .name(identity.name().trim())
                    .email(identity.email().trim().toLowerCase(Locale.ROOT))
                    .sourcePointUserId(identity.sourcePointUserId())
                    .age(null)
                    .maritalStatus(UNSPECIFIED_MARITAL_STATUS)
                    .build();
                return userRepository.saveAndFlush(user);
            }

            user.setSourcePointUserId(identity.sourcePointUserId());
            changed = true;
        }

        if (!user.getEmail().equalsIgnoreCase(identity.email())) {
            User emailOwner = userRepository.findByEmailIgnoreCase(identity.email()).orElse(null);
            if (emailOwner != null && !emailOwner.getId().equals(user.getId())) {
                throw new ApiException(HttpStatus.CONFLICT, "The SourcePoint email matches another finance profile");
            }
            user.setEmail(identity.email().trim().toLowerCase(Locale.ROOT));
            changed = true;
        }
        return changed ? userRepository.saveAndFlush(user) : user;
    }

    @Transactional(readOnly = true)
    public User getCurrentUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !(authentication.getPrincipal() instanceof SourcePointPrincipal principal)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "SourcePoint authentication required");
        }
        return userRepository.findBySourcePointUserId(principal.sourcePointUserId())
            .orElseThrow(() -> new ApiException(HttpStatus.UNAUTHORIZED, "SourcePoint profile is not linked"));
    }
}
