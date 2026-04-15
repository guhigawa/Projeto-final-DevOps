import os, json
from datetime import datetime
#Creating class to handle evidence logging
class EvidenceLogger:
    
    def __init__(self, test_suite_name,base_url):
        self.test_suite_name = test_suite_name
        self.base_url = base_url
        self.evidence_dir = "user-service/tests/evidence"
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
            f.write(f"Projeto:WebApp Final Project - User service\n")
            f.write(f"test suite: {self.test_suite_name}\n")
            f.write("=" * 80 + "\n\n")#final separator line
    
    def log_test_result(self, test_name, status, details="", response_data=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "PASS" if status else "FAIL"

        log_entry = f"[{timestamp}] - {test_name} - {status}\n"
        if details:
            log_entry += f"Details: {details}\n"
        if response_data:
            formatted_data = json.dumps(response_data, indent=2, ensure_ascii=False)
            log_entry += f"response:{formatted_data}\n"
        log_entry += "-" * 40 + "\n"

        with open(self.evidence_file,'a', encoding='utf-8') as f:
            f.write(log_entry)

        print(log_entry)