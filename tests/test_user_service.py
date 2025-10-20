import pytest, requests, json, time, os, sys;
from datetime import datetime


BASE_URL = "http://localhost:3001"


#Creating class to handle evidence logging
class TestUserEvidence:
    
    def __init__(self, test_suite_name):
        self.test_suite_name = test_suite_name
        self.evidence_dir = "tests/evidence"
        self.setup_evidence_system()

    def setup_evidence_system(self):
        if not os.path.exists(self.evidence_dir):
            os.makedirs(self.evidence_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.evidence_file = f"{self.evidence_dir}/tests_evidence_{timestamp}.txt"

        with open(self.evidence_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n") #Creating header for evidence file with 80 characters
            f.write("TESTS EVIDENCE - USER SERVICE\n")# Title of the evidence file
            f.write("=" * 80 + "\n")#Creating a separator line for the second title
            f.write(f"Date and Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n") 
            f.write(f"Projeto: Authentication Service - User service\n")
            f.write(f"test suite: {self.test_suite_name}\n")
            f.write("=" * 80 + "\n\n")#final separator line
    
    def log_test_result(self, test_name, status, detail="", response_data=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "PASS" if status else "FAIL"

        log_entry = f"[{timestamp}] - {test_name} - {status}\n"
        if detail:
            log_entry += f"Details: {detail}\n"
        if response_data:
            log_entry += f"Response Data: {json.dumps(response_data, indent=2)}\n"
        log_entry += "\n"

        with open(self.evidence_file,'a', encoding='utf-8') as f:
            f.write(log_entry)

        print(log_entry)

class TestUserService:
    