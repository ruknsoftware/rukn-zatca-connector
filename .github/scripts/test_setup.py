#!/usr/bin/env python3
"""
Test environment setup script for KSA Compliance CI/CD pipeline.
This script prepares the test environment by running custom ERPNext setup,
data setup, and ZATCA test preparation.
"""

import frappe
import sys
import os


def main():
    """Main function to run the test environment setup."""
    print("🚀 Starting test environment setup...")
    
    try:
        # Import test setup functions
        from ksa_compliance.test.test_setup import custom_erpnext_setup, data_setup
        from ksa_compliance.ksa_compliance.test.zatca_test_preparation import prepare_system_for_zatca_tests
        
        # Run the test setup
        print("🚀 Running custom_erpnext_setup...")
        custom_erpnext_setup()
        
        print("🚀 Running data_setup...")
        data_setup()
        
        print("🚀 Running ZATCA test preparation...")
        prepare_system_for_zatca_tests()
        
        print("✅ Test environment setup completed!")
        
    except Exception as e:
        print(f"❌ Error during test environment setup: {str(e)}")
        raise


if __name__ == "__main__":
    main()
