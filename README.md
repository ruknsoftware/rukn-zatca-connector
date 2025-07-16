KSA Compliance
--------------

A comprehensive Frappe application developed by Rukn Software for KSA Compliance (ZATCA Integration), providing advanced features and full support for both Phase 1 and Phase 2 requirements. Our enhanced version includes extensive improvements and new capabilities to meet complex business needs.

### Main Features

1.  ZATCA Phase 1 - compliance
2.  ZATCA Phase 2 - compliance
3.  Simplified invoice
4.  Standard Invoice
5.  Wizard onboarding
6.  Automatic ZATCA CLI setup
7.  Tax exemption reasons
8.  ZATCA dashboard
9.  Embedded Invoice QR without impacting storage
10. Embedded Invoice XML without impacting storage
11. ZATCA phase 1 print format
12. ZATCA phase 2 print format
13. Resend process
14. Rejection process
15. ZATCA Integration Live and Batch modes
16. Multi-company support
17. Multi-device setup
18. Embedded compliance checks log
19. System XML validation
20. Support ZATCA Sandbox
21. Advanced Payment Entry System:
    * Dedicated advance payment configuration
    * Automated payment entry generation
    * Comprehensive settlement calculations
    * ZATCA-compliant reconciliation controls
22. Return Invoice Management
23. POS Invoice Integration

### How to Install

-   **Frappe Cloud:**\
    Comming Soon !!
-   **Self Hosting:**

```
bench get-app --branch master https://github.com/ruknsoftware/ksa_compliance.git
```

```
bench setup requirements
```

```
bench  --site [your.site.name] install-app ksa_compliance
```

```
bench  --site [your.site.name] migrate
```

```
bench restart
```

### Support

For support and assistance:
- Create issues in our repository: https://github.com/ruknsoftware/ksa_compliance/issues
- Email us at: alaa@rukn-software.com

### New Features and Bug report:

Please create issues in our repository with the following information:
- Bench information (output of `bench version`)
- For invoice rejections:
  - Generated invoice XML (from `Sales Invoice Additional Fields`)
  - Any validation warnings/errors
  - Screenshots of the `Sales Invoice` document

### Contributing

We follow the same guidelines as ERPNext:

1. [**Issue Guidelines**](https://github.com/frappe/erpnext/wiki/Issue-Guidelines)
2. [**Pull Request Requirements**](https://github.com/frappe/erpnext/wiki/Contribution-Guidelines)

### License and Attribution

This application is licensed under AGPL and builds upon the foundational work of the original KSA Compliance app. Rukn Software has significantly enhanced the application with new features, improvements, and enterprise-grade capabilities.

Copyright (c) 2025 Rukn Software
Original foundation Copyright (c) 2024 LavaLoon
