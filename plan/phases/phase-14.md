# Phase 14: MFA & HSM + JIT Provisioning

## Status
- [ ] Refinement complete
- [ ] Implementation in progress
- [ ] Implementation complete
- [ ] Phase review complete

## Goal
Enhanced authentication security with MFA and HSM for critical operations, plus JIT (Just-In-Time) user/group provisioning from OIDC/SAML identity providers.

*Was old Phase 12 (MFA & HSM). Gains JIT provisioning from old Phase 11 (OIDC/SAML — core IdP config already done in Phase 3).*

## Deliverables
- TOTP MFA setup and verification
- WebAuthn/Yubikey support (demo mode)
- HSM integration via PKCS#11 (production)
- Tier-based MFA enforcement configuration
- MFA recovery codes
- MFA setup flow in frontend
- HSM operation signing
- JIT user auto-provisioning from OIDC/SAML claims
- JIT group auto-provisioning from IdP claims
- IdP-initiated SSO flows

## Dependencies
- Phase 3 complete (IdP configuration, permission system for role mapping)

## Key Questions for Refinement
- Which HSM providers to support?
- How to handle HSM unavailability?
- Should MFA be required or optional per tier?
- How many recovery codes to generate?
- How to handle JIT-provisioned user conflicts with existing accounts?
- How to handle IdP disconnection / user deprovisioning?
- Should JIT provisioning be optional per IdP?

## Estimated Tasks
~12-14 tasks (to be refined before implementation)
