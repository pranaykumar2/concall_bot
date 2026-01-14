
import unittest
import sys
import os
import logging

# Add current directory to path
sys.path.append(os.getcwd())

from concall import normalize_company_name, fuzzy_match_company

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestMatching")

class TestCompanyMatching(unittest.TestCase):
    def setUp(self):
        # Mock Nifty 500 data
        self.nifty_companies = {
            "HDFC Asset Management Company Ltd.",
            "Tata Consultancy Services Ltd.",
            "Reliance Industries Ltd.",
            "ICICI Lombard General Insurance Company Ltd.",
            "ICICI Prudential Life Insurance Company Ltd.",
            "Sun Pharmaceutical Industries Ltd.",
            "Motherson Sumi Systems Ltd.",
            "Chambal Fertilizers & Chemicals Ltd.",
            "Gujarat State Petronet Ltd.",
            "Power Grid Corporation of India Ltd.",
            "L&T Technology Services Ltd.",
            "Indian Railway Catering And Tourism Corporation Ltd."
        }
        
        self.company_map = {
            normalize_company_name(c): c for c in self.nifty_companies
        }

    def test_hdfc_amc_failure_case(self):
        """Test the specific reported issue"""
        api_name = "HDFC Asset Mngt. Co"
        match = fuzzy_match_company(api_name, self.nifty_companies, self.company_map)
        self.assertEqual(match, "HDFC Asset Management Company Ltd.", 
                         f"Failed to match '{api_name}'")

    def test_abbreviation_variations(self):
        """Test common corporate abbreviations"""
        test_cases = [
            ("Reliance Ind.", "Reliance Industries Ltd."),
            ("ICICI Lombard Gen. Ins.", "ICICI Lombard General Insurance Company Ltd."),
            ("Sun Pharm. Ind.", "Sun Pharmaceutical Industries Ltd."),
            ("Motherson Sumi Syst.", "Motherson Sumi Systems Ltd."),
            ("Chambal Fert. & Chem.", "Chambal Fertilizers & Chemicals Ltd."),
            ("Guj. State Petro.", "Gujarat State Petronet Ltd."),
            ("Power Grid Corpn.", "Power Grid Corporation of India Ltd.")
        ]
        
        for api_name, expected in test_cases:
            with self.subTest(api_name=api_name):
                match = fuzzy_match_company(api_name, self.nifty_companies, self.company_map)
                self.assertEqual(match, expected, 
                                 f"Failed to match '{api_name}'")

    def test_normalization(self):
        """Test specific normalization rules"""
        cases = {
            "HDFC Asset Mngt.": "hdfc asset management",
            "ABC Corpn.": "abc corporation",
            "Global Comm.": "global communications",
            "Super Eng.": "super engineering"
        }
        
        for input_name, expected_part in cases.items():
            normalized = normalize_company_name(input_name)
            self.assertTrue(expected_part in normalized, 
                            f"Normalization of '{input_name}' -> '{normalized}' did not contain '{expected_part}'")

if __name__ == '__main__':
    unittest.main()
