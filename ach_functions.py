"""Helper functions for ACH reading"""
from datetime import datetime
import os.path


class ACHFileReader(object):
    """Read ACH Files"""
    LINE_LENGTH = 94

    def __init__(self, file_name):
        if not os.path.isfile(file_name):
            raise ValueError('Path not found {} '.format(file_name))
        self.file_name = file_name
        self.file_header = {}
        self.file_control_record = {}
        self.batch_headers = []
        self.batch_control_records = []
        self.entries = []
        self.addenda_records = []
        self.read_file()

    SERVICE_CLASS_CODES = {'200': 'Mixed',
                           '220': 'Credits Only',
                           '225': 'Debits Only',
                           '280': 'Automated Accounting Advices'}

    TRANSACTION_CODES = {'22': 'Demand Credit - Automated Payment/Deposit',
                         '21': 'Demand Credit - Return Or NOC',
                         '23': 'Demand Credit - Prenote',
                         '24': 'Demand Credit - Zero Dollar',
                         '31': 'Savings Credit - Return Or NOC',
                         '32': 'Savings Credit - Automated Payment/Deposit',
                         '33': 'Savings Credit - Prenote',
                         '34': 'Savings Credit - Zero Dollar',
                         '26': 'Demand Debit - Return Or NOC',
                         '27': 'Demand Debit - Automated Payment/Deposit',
                         '37': 'Savings Debit - Automated Payment/Deposit',
                         '42': 'GL Credit - Automated Payment/Deposit',
                         '47': 'GL Debit - Automated Payment/Deposit',
                         '52': 'Loan Credit - Automated Payment/Deposit',
                         '55': 'Loan Debit - Reversal',
                         '36': 'Savings Debit - Return Or NOC',
                         '41': 'GL Credit - Return Or NOC',
                         '46': 'GL Debit - Return Or NOC',
                         '51': 'Loan Credit - Return Or NOC',
                         '56': 'Loan Debit - Return Or NOC',
                         '28': 'Demand Debit - Prenote',
                         '38': 'Savings Debit - Prenote'}

    def read_file(self):
        """Read the ach file with given filename"""
        try:
            with open(self.file_name, 'r') as ach_file:
                file_contents = ach_file.read().replace('\n', '').replace('\r', '')

            self._parse_ach_file(file_contents)
        except FileNotFoundError as err:
            print("File does not exist -> " + str(err))

    def _parse_ach_file(self, contents):
        """Read the ach file"""
        file_length = len(contents)

        for index in range(0, file_length, self.LINE_LENGTH):
            line = contents[index:index + self.LINE_LENGTH]

            if line.startswith('1'):
                self._read_header(line)
            elif line.startswith('5'):
                self._read_batch_header(line)
            elif line.startswith('6'):
                self._read_entry_detail(line)
            elif line.startswith('7'):
                self._read_addenda_record(line)
            elif line.startswith('8'):
                self._read_batch_control_record(line)
            elif line.startswith('9'):
                if line == '9' * 94:
                    continue
                self._read_file_control_record(line)

    def _read_header(self, line):
        """Parses a standard ACH File Header Line"""
        try:
            creation_date = datetime.strptime(line[23:33], '%y%m%d%H%M')
        except ValueError as err:
            print('Error parsing file creation date -> ' + str(err))
            creation_date = '000000'

        self.file_header = {'Priority Code': line[1:3],
                            'Immediate Destination':  line[3:13].strip(),
                            'Immediate Origin': line[13:23],
                            'Creation Date': creation_date,
                            'File ID Modifier': line[33],
                            'Record Size': int(line[34:37].strip()),
                            'Blocking Factor': int(line[37:39]),
                            'Format Code': line[39],
                            'Immediate Destination Name': line[40:63].strip(),
                            'Immediate Origin Name': line[63:86].strip(),
                            'Reference Code': line[86:93]}



    def _read_entry_detail(self, line):
        """Read an entry detail Line"""
        account_number = 0
        try:
            account_number = int(line[12:29].strip().replace('-', ''))
        except ValueError as err:
            print('Error parsing account number field -> ' + str(err))

        result_dict = {'Transaction Code': line[1:3],
                       'ReceivingID': line[3:11],
                       'CheckDigit': line[11],
                       'Account Number': account_number,
                       'Amount': int(line[29:39]) / 100,
                       'Individual ID': line[39:54],
                       'Receiver Name': line[54:76].strip(),
                       'DiscretionaryData': line[76:78],
                       'AddendaIndicator': line[78],
                       'TraceNumber': line[79:94]}

        self.entries.append(result_dict)

    def _read_addenda_record(self, line):
        """Read an addenda record"""
        addenda_dict = {'Addenda Type Code:': line[1:3],
                        'Payment Related Info': line[3:83].strip(),
                        'Addenda Sequence Number': line[83:87],
                        'Entry Detail Sequence Number': line[87:94]}
        self.addenda_records.append(addenda_dict)
    
    def _read_batch_header(self, line):
        """Parse a batch header line"""
        try:
            effective_entry_date = datetime.strptime(line[69:75], '%y%m%d')
        except ValueError as err:
            print('Error parsing effective entry date -> ' + str(err))
            effective_entry_date = '00000000'

        batch_header_dict = {'Service Class Code': line[1:4],
                             'Company Name': line[4:20].strip(),
                             'Company Discretionary Data': line[20:40].strip(),
                             'Company ID': line[40:50].strip(),
                             'SEC Code': line[50:53],
                             'Company Entry Description': line[53:63].strip(),
                             'Company Descriptive Date': line[63:69].strip(),
                             'Effective Entry Date': effective_entry_date,
                             'Settlement Date Julian': line[75:78],
                             'Originator Status Code': line[78],
                             'Originating DFI ID': line[79:87],
                             'Batch Number': line[87:94]}
        self.batch_headers.append(batch_header_dict)

    def _read_batch_control_record(self, line):
        """Read batch control record"""
        bcr_dict = {'Service Class Code':  line[1:4],
                    'Entry Addenda Count': line[4:10],
                    'Entry Hash': line[10:20],
                    'Total Debit Amount': int(line[20:32]) / 100,
                    'Total Credit Amount': int(line[32:44]) / 100,
                    'Company ID': line[44:54],
                    'Message Auth Code': line[54:73].strip(),
                    'Originating DFI ID': line[79:87],
                    'Batch Number': line[87:94]}
        self.batch_control_records.append(bcr_dict)

    def _read_file_control_record(self, line):
        """Read file control record"""
        self.file_control_record = {'Batch Count': int(line[1:7]),
                                    'Block Count': int(line[7:13]),
                                    'Addenda Count': int(line[13:21]),
                                    'Entry Hash': line[21:31],
                                    'Total Debit Amount': int(line[31:43]) / 100,
                                    'Total Credit Amount': int(line[43:55]) / 100,
                                    'Reserved Data': line[55:94].strip()}

    def describe(self):
        """Print Details about the ACH File"""
        print('File Name: ' + self.file_name)
        print('File create date: {}'.format(self.file_header['Creation Date']))
        print('Batch Count: ' + str(self.file_control_record.get('Batch Count')))
        print('Total Debit Amount: ' +
              str(self.file_control_record.get('Total Debit Amount')))
        print("Total Credit Amount: " +
              str(self.file_control_record.get("Total Credit Amount")))

    def pp_all_entries(self):
        """Pretty Print all entries"""
        for entry in self.entries:
            self.pp_entry(entry)

    def pp_entry(self, entry):
        """Pretty Print an entry item"""
        print('Tran Code: {} {}'.format(entry['Transaction Code'],
                                        self.TRANSACTION_CODES[entry['Transaction Code']]))
        print('Account Number: {} Individual ID: {}'.format(entry['Account Number'],
                                                            entry['Individual ID']))
        print('Amount: {}'.format(entry['Amount']))
    
    def pp_all_batches(self):
        """Pretty print all batches"""
        for batch in self.batch_headers:
            self.pp_batch(batch)

    def pp_batch(self, batch):
        """Pretty print a single batch"""
        print('SEC Code: ' + batch['SEC Code'])
        
    def search_by_account_number(self, account_num):
        """Search all entries for a specific account number"""
        for entry in self.entries:
            if entry['Account Number'] == account_num:
                self.pp_entry(entry)
