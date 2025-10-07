# ZATCA Test Preparation Guide

This guide outlines the necessary system configuration steps that must be completed before running ZATCA compliance tests.

## Required Settings

### 1. Disable Rounded Total ✅ (Available in v14)
- **Location**: Global Defaults → "Disable Rounded Total"
- **Action**: Enable this checkbox
- **Purpose**: Hides the 'Rounded Total' field in transactions as required by ZATCA

### 2. Configure SAR Currency Smallest Fraction ✅ (Available in v14)
- **Location**: Currency → SAR → "Smallest Currency Fraction Value"
- **Action**: Set to `0.01`
- **Additional**: Ensure `fraction_units` is set to `100` and `fraction` is "Halala"
- **Purpose**: Ensures proper currency handling for Saudi Riyal

### 3. Set Float Precision to 2 ✅ (Available in v14)
- **Location**: System Settings → "Float Precision"
- **Action**: Set to `2`
- **Purpose**: Ensures consistent decimal handling

### 4. Set Currency Precision to 2 ✅ (Available in v14)
- **Location**: System Settings → "Currency Precision"
- **Action**: Set to `2`
- **Purpose**: Ensures currency amounts are displayed with 2 decimal places

### 5. Change Rounding Method to Banker's Rounding ✅ (Available in v14)
- **Location**: System Settings → "Rounding Method"
- **Action**: Set to "Banker's Rounding" (not the legacy version)
- **Purpose**: Ensures proper rounding for ZATCA compliance

### 6. Round Tax Amount Row-wise ⚠️ (Version Dependent)
- **Frappe v14**: Available via `round_tax_amount_row_wise` app
- **Frappe v15+**: Built-in feature in Account Settings
- **Action**: 
  - **v14**: Ensure the app is installed and enabled
  - **v15+**: Activate the setting in Account Settings

## Automated Preparation

### Using Bench Console
```bash
# From frappe-bench directory
bench --site <your-site> console
```
Then in the console:
```python
from ksa_compliance.ksa_compliance.utils.zatca_test_preparation import prepare_system_for_zatca_tests
prepare_system_for_zatca_tests()
```

### or Using Bench Command
```bash
# From frappe-bench directory
bench --site <your-site> execute ksa_compliance.ksa_compliance.commands.prepare_zatca_tests.prepare_for_zatca
```

## Manual Configuration

If you prefer to configure manually, follow these steps:

### Step 1: Global Defaults
1. Go to **Setup** → **Global Defaults**
2. Check the **"Disable Rounded Total"** checkbox
3. Save

### Step 2: System Settings
1. Go to **Setup** → **System Settings**
2. Set **Float Precision** to `2`
3. Set **Currency Precision** to `2`
4. Set **Rounding Method** to `Banker's Rounding`
5. Save

### Step 3: SAR Currency
1. Go to **Setup** → **Currency**
2. Open **SAR** currency
3. Set **Smallest Currency Fraction Value** to `0.01`
4. Set **Fraction Units** to `100`
5. Set **Fraction** to `Halala`
6. Save

### Step 4: Configure Round Tax Row-wise

#### For Frappe v14:
1. Go to **Apps** → **Installed Apps**
2. Verify that `round_tax_amount_row_wise` is installed and enabled
3. If not installed, install it from RUKN github

#### For Frappe v15+:
1. Go to **Accounts** → **Settings** → **Account Settings**
2. Check the **"Round Tax Amount Row-wise"** checkbox
3. Save the settings

## Version Compatibility

| Feature | Frappe v14 | Frappe v15 | Notes |
|---------|------------|------------|-------|
| Disable Rounded Total | ✅ | ✅ | Available in both versions |
| Currency Smallest Fraction | ✅ | ✅ | Available in both versions |
| Float/Currency Precision | ✅ | ✅ | Available in both versions |
| Banker's Rounding | ✅ | ✅ | Available in both versions |
| Round Tax Row-wise | ⚠️ | ✅ | Requires app in v14, built-in v15 (Account Settings) |
