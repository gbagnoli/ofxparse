from datetime import datetime, timedelta
from decimal import Decimal
from unittest import TestCase
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from bs4 import BeautifulSoup
import sys
sys.path.append('..')

from support import open_file
from ofxparse import OfxParser, AccountType, Account, Statement, Transaction
from ofxparse.ofx import OfxFile, OfxParserException

try:
    stringtype = unicode

except NameError:
    stringtype = str

class TestOfxFile(TestCase):
    def testHeaders(self):
        expect = {"OFXHEADER": u"100",
                  "DATA": u"OFXSGML",
                  "VERSION": u"102",
                  "SECURITY": None,
                  "ENCODING": u"USASCII",
                  "CHARSET": u"1252",
                  "COMPRESSION": None,
                  "OLDFILEUID": None,
                  "NEWFILEUID": None,
                  }
        ofx = OfxParser.parse(open_file('bank_medium.ofx'))
        self.assertEqual(expect, ofx.headers)

    def testUTF8(self):
        fh = StringIO("""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UNICODE
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

""")
        ofx_file = OfxFile(fh)
        headers = ofx_file.headers
        data = ofx_file.fh.read()

        self.assertTrue(type(data) is stringtype)
        for key, value in headers.items():
            self.assertTrue(type(key) is stringtype)
            self.assertTrue(type(value) is not str)

    def testCP1252(self):
        fh = StringIO("""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET: 1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
""")
        ofx_file = OfxFile(fh)
        headers = ofx_file.headers
        result = ofx_file.fh.read()

        self.assertTrue(type(result) is stringtype)
        for key, value in headers.items():
            self.assertTrue(type(key) is stringtype)
            self.assertTrue(type(value) is not str)

    def testUTF8Japanese(self):
        fh = StringIO("""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:CSUNICODE
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
""")
        ofx_file = OfxFile(fh)
        headers = ofx_file.headers
        result = ofx_file.fh.read()

        self.assertTrue(type(result) is stringtype)
        for key, value in headers.items():
            self.assertTrue(type(key) is stringtype)
            self.assertTrue(type(value) is not str)

    def testBrokenLineEndings(self):
        fh = StringIO("OFXHEADER:100\rDATA:OFXSGML\r")
        ofx_file = OfxFile(fh)
        self.assertEqual(len(ofx_file.headers.keys()), 2)


class TestParse(TestCase):
    def testEmptyFile(self):
        fh = StringIO("")
        self.assertRaises(OfxParserException, OfxParser.parse, fh)

    def testThatParseWorksWithoutErrors(self):
        OfxParser.parse(open_file('bank_medium.ofx'))

    def testThatParseFailsIfNothingToParse(self):
        self.assertRaises(TypeError, OfxParser.parse, None)

    def testThatParseFailsIfAPathIsPassedIn(self):
        # A file handle should be passed in, not the path.
        self.assertRaises(RuntimeError, OfxParser.parse, '/foo/bar')

    def testThatParseReturnsAResultWithABankAccount(self):
        ofx = OfxParser.parse(open_file('bank_medium.ofx'))
        self.assertTrue(ofx.account is not None)

    def testEverything(self):
        ofx = OfxParser.parse(open_file('bank_medium.ofx'))
        self.assertEqual('12300 000012345678', ofx.account.number)
        self.assertEqual('160000100', ofx.account.routing_number)
        self.assertEqual('CHECKING', ofx.account.account_type)
        self.assertEqual(Decimal('382.34'), ofx.account.statement.balance)
        # Todo: support values in decimal or int form.
        # self.assertEqual('15',
        # ofx.bank_account.statement.balance_in_pennies)
        self.assertEqual(
            Decimal('682.34'), ofx.account.statement.available_balance)
        self.assertEqual(
            datetime(2009, 4, 1), ofx.account.statement.start_date)
        self.assertEqual(
            datetime(2009, 5, 23, 12, 20, 17), ofx.account.statement.end_date)

        self.assertEqual(3, len(ofx.account.statement.transactions))

        transaction = ofx.account.statement.transactions[0]
        self.assertEqual("MCDONALD'S #112", transaction.payee)
        self.assertEqual('pos', transaction.type)
        self.assertEqual(Decimal('-6.60'), transaction.amount)
        # Todo: support values in decimal or int form.
        # self.assertEqual('15', transaction.amount_in_pennies)

    def testMultipleAccounts(self):
        ofx = OfxParser.parse(open_file('multiple_accounts2.ofx'))
        self.assertEqual(2, len(ofx.accounts))
        self.assertEqual('9100', ofx.accounts[0].number)
        self.assertEqual('9200', ofx.accounts[1].number)
        self.assertEqual('123', ofx.accounts[0].routing_number)
        self.assertEqual('123', ofx.accounts[1].routing_number)
        self.assertEqual('CHECKING', ofx.accounts[0].account_type)
        self.assertEqual('SAVINGS', ofx.accounts[1].account_type)


class TestStringToDate(TestCase):
    ''' Test the string to date parser '''
    def test_bad_format(self):
        ''' A poorly formatted string should throw a ValueError '''

        bad_string = 'abcdLOL!'
        self.assertRaises(ValueError, OfxParser.parseOfxDateTime, bad_string)

        bad_but_close_string = '881103'
        self.assertRaises(ValueError, OfxParser.parseOfxDateTime, bad_string)

        no_month_string = '19881301'
        self.assertRaises(ValueError, OfxParser.parseOfxDateTime, bad_string)

    def test_parses_correct_time(self):
        '''Test whether it can parse correct time for some valid time fields'''
        self.assertEqual(OfxParser.parseOfxDateTime('19881201'),
                          datetime(1988, 12, 1, 0, 0))
        self.assertEqual(OfxParser.parseOfxDateTime('19881201230100'),
                          datetime(1988, 12, 1, 23, 1))
        self.assertEqual(OfxParser.parseOfxDateTime('20120229230100'),
                          datetime(2012, 2, 29, 23, 1))

    def test_parses_time_offset(self):
        ''' Test that we handle GMT offset '''
        self.assertEqual(OfxParser.parseOfxDateTime('20001201120000 [0:GMT]'),
                          datetime(2000, 12, 1, 12, 0))
        self.assertEqual(OfxParser.parseOfxDateTime('19991201120000 [1:ITT]'),
                          datetime(1999, 12, 1, 11, 0))
        self.assertEqual(
            OfxParser.parseOfxDateTime('19881201230100 [-5:EST]'),
            datetime(1988, 12, 2, 4, 1))
        self.assertEqual(
            OfxParser.parseOfxDateTime('20120229230100 [-6:CAT]'),
            datetime(2012, 3, 1, 5, 1))
        self.assertEqual(
            OfxParser.parseOfxDateTime('20120412120000 [-5.5:XXX]'),
            datetime(2012, 4, 12, 17, 30))
        self.assertEqual(
            OfxParser.parseOfxDateTime('20120412120000 [-5:XXX]'),
            datetime(2012, 4, 12, 17))
        self.assertEqual(
            OfxParser.parseOfxDateTime('20120922230000 [+9:JST]'),
            datetime(2012, 9, 22, 14, 0))


class TestParseStmtrs(TestCase):
    input = '''
<STMTRS><CURDEF>CAD<BANKACCTFROM><BANKID>160000100<ACCTID>12300 000012345678<ACCTTYPE>CHECKING</BANKACCTFROM>
<BANKTRANLIST><DTSTART>20090401<DTEND>20090523122017
<STMTTRN><TRNTYPE>POS<DTPOSTED>20090401122017.000[-5:EST]<TRNAMT>-6.60<FITID>0000123456782009040100001<NAME>MCDONALD'S #112<MEMO>POS MERCHANDISE;MCDONALD'S #112</STMTTRN>
</BANKTRANLIST><LEDGERBAL><BALAMT>382.34<DTASOF>20090523122017</LEDGERBAL><AVAILBAL><BALAMT>682.34<DTASOF>20090523122017</AVAILBAL></STMTRS>
    '''

    def testThatParseStmtrsReturnsAnAccount(self):
        stmtrs = BeautifulSoup(self.input)
        account = OfxParser.parseStmtrs(
            stmtrs.find('stmtrs'), AccountType.Bank)[0]
        self.assertEqual('12300 000012345678', account.number)
        self.assertEqual('160000100', account.routing_number)
        self.assertEqual('CHECKING', account.account_type)

    def testThatReturnedAccountAlsoHasAStatement(self):
        stmtrs = BeautifulSoup(self.input)
        account = OfxParser.parseStmtrs(
            stmtrs.find('stmtrs'), AccountType.Bank)[0]
        self.assertTrue(hasattr(account, 'statement'))


class TestAccount(TestCase):
    def testThatANewAccountIsValid(self):
        account = Account()
        self.assertEqual('', account.number)
        self.assertEqual('', account.routing_number)
        self.assertEqual('', account.account_type)
        self.assertEqual(None, account.statement)


class TestParseStatement(TestCase):
    def testThatParseStatementReturnsAStatement(self):
        input = '''
<STMTTRNRS>
 <TRNUID>20090523122017
 <STATUS>
  <CODE>0
  <SEVERITY>INFO
  <MESSAGE>OK
 </STATUS>
 <STMTRS>
  <CURDEF>CAD
  <BANKACCTFROM>
   <BANKID>160000100
   <ACCTID>12300 000012345678
   <ACCTTYPE>CHECKING
  </BANKACCTFROM>
  <BANKTRANLIST>
   <DTSTART>20090401
   <DTEND>20090523122017
   <STMTTRN>
    <TRNTYPE>POS
    <DTPOSTED>20090401122017.000[-5:EST]
    <TRNAMT>-6.60
    <FITID>0000123456782009040100001
    <NAME>MCDONALD'S #112
    <MEMO>POS MERCHANDISE;MCDONALD'S #112
   </STMTTRN>
  </BANKTRANLIST>
  <LEDGERBAL>
   <BALAMT>382.34
   <DTASOF>20090523122017
  </LEDGERBAL>
  <AVAILBAL>
   <BALAMT>682.34
   <DTASOF>20090523122017
  </AVAILBAL>
 </STMTRS>
</STMTTRNRS>
        '''
        txn = BeautifulSoup(input)
        statement = OfxParser.parseStatement(txn.find('stmttrnrs'))
        self.assertEqual(datetime(2009, 4, 1), statement.start_date)
        self.assertEqual(
            datetime(2009, 5, 23, 12, 20, 17), statement.end_date)
        self.assertEqual(1, len(statement.transactions))
        self.assertEqual(Decimal('382.34'), statement.balance)
        self.assertEqual(Decimal('682.34'), statement.available_balance)


class TestStatement(TestCase):
    def testThatANewStatementIsValid(self):
        statement = Statement()
        self.assertEqual('', statement.start_date)
        self.assertEqual('', statement.end_date)
        self.assertEqual(0, len(statement.transactions))


class TestParseTransaction(TestCase):
    def testThatParseTransactionReturnsATransaction(self):
        input = '''
<STMTTRN>
 <TRNTYPE>POS
 <DTPOSTED>20090401122017.000[-5:EST]
 <TRNAMT>-6.60
 <FITID>0000123456782009040100001
 <NAME>MCDONALD'S #112
 <MEMO>POS MERCHANDISE;MCDONALD'S #112
</STMTTRN>
'''
        txn = BeautifulSoup(input)
        transaction = OfxParser.parseTransaction(txn.find('stmttrn'))
        self.assertEqual('pos', transaction.type)
        self.assertEqual(datetime(
            2009, 4, 1, 12, 20, 17) - timedelta(hours=-5), transaction.date)
        self.assertEqual(Decimal('-6.60'), transaction.amount)
        self.assertEqual('0000123456782009040100001', transaction.id)
        self.assertEqual("MCDONALD'S #112", transaction.payee)
        self.assertEqual("POS MERCHANDISE;MCDONALD'S #112", transaction.memo)


class TestTransaction(TestCase):
    def testThatAnEmptyTransactionIsValid(self):
        t = Transaction()
        self.assertEqual('', t.payee)
        self.assertEqual('', t.type)
        self.assertEqual(None, t.date)
        self.assertEqual(None, t.amount)
        self.assertEqual('', t.id)
        self.assertEqual('', t.memo)


class TestInvestmentAccount(TestCase):
    sample = '''
<?xml version="1.0" encoding="UTF-8" ?>
<?OFX OFXHEADER="200" VERSION="200" SECURITY="NONE"
  OLDFILEUID="NONE" NEWFILEUID="NONE" ?>
<OFX>
 <INVSTMTMSGSRSV1>
  <INVSTMTTRNRS>
   <TRNUID>38737714201101012011062420110624</TRNUID>
   <STATUS>
    <CODE>0</CODE>
    <SEVERITY>INFO</SEVERITY>
   </STATUS>
   <INVSTMTRS>
   </INVSTMTRS>
  </INVSTMTTRNRS>
 </INVSTMTMSGSRSV1>
</OFX>
'''

    def testThatParseCanCreateAnInvestmentAccount(self):
        OfxParser.parse(StringIO(self.sample))
        # Success!



class TestVanguardInvestmentStatement(TestCase):
    def testForUnclosedTags(self):
        ofx = OfxParser.parse(open_file('vanguard.ofx'))
        self.assertTrue(hasattr(ofx, 'account'))
        self.assertTrue(hasattr(ofx.account, 'statement'))
        self.assertTrue(hasattr(ofx.account.statement, 'transactions'))
        self.assertEqual(len(ofx.account.statement.transactions), 1)
        self.assertEqual(ofx.account.statement.transactions[0].id,
                          '01234567890.0123.07152011.0')
        self.assertEqual(ofx.account.statement.transactions[0]
                          .tradeDate, datetime(2011, 7, 15, 21))
        self.assertEqual(ofx.account.statement.transactions[0]
                          .settleDate, datetime(2011, 7, 15, 21))
        self.assertTrue(hasattr(ofx.account.statement, 'positions'))
        self.assertEqual(len(ofx.account.statement.positions), 2)
        self.assertEqual(
            ofx.account.statement.positions[0].units, Decimal('102.0'))

    def testSecurityListSuccess(self):
        ofx = OfxParser.parse(open_file('vanguard.ofx'))
        self.assertEqual(len(ofx.security_list), 2)


class TestFidelityInvestmentStatement(TestCase):
    def testForUnclosedTags(self):
        ofx = OfxParser.parse(open_file('fidelity.ofx'))
        self.assertTrue(hasattr(ofx.account.statement, 'positions'))
        self.assertEqual(len(ofx.account.statement.positions), 6)
        self.assertEqual(
            ofx.account.statement.positions[0].units, Decimal('128.0'))

    def testSecurityListSuccess(self):
        ofx = OfxParser.parse(open_file('fidelity.ofx'))
        self.assertEqual(len(ofx.security_list), 7)


class TestAccountInfoAggregation(TestCase):
    def testForFourAccounts(self):
        ofx = OfxParser.parse(open_file('account_listing_aggregation.ofx'))
        self.assertTrue(hasattr(ofx, 'accounts'))
        self.assertEqual(len(ofx.accounts), 4)

        # first account
        account = ofx.accounts[0]
        self.assertEqual(account.account_type, 'SAVINGS')
        self.assertEqual(account.desc, 'USAA SAVINGS')
        self.assertEqual(account.institution.organization, 'USAA')
        self.assertEqual(account.number, '0000000001')
        self.assertEqual(account.routing_number, '314074269')

        # second
        account = ofx.accounts[1]
        self.assertEqual(account.account_type, 'CHECKING')
        self.assertEqual(account.desc, 'FOUR STAR CHECKING')
        self.assertEqual(account.institution.organization, 'USAA')
        self.assertEqual(account.number, '0000000002')
        self.assertEqual(account.routing_number, '314074269')

        # third
        account = ofx.accounts[2]
        self.assertEqual(account.account_type, 'CREDITLINE')
        self.assertEqual(account.desc, 'LINE OF CREDIT')
        self.assertEqual(account.institution.organization, 'USAA')
        self.assertEqual(account.number, '00000000000003')
        self.assertEqual(account.routing_number, '314074269')

        # fourth
        account = ofx.accounts[3]
        self.assertEqual(account.account_type, '')
        self.assertEqual(account.desc, 'MY CREDIT CARD')
        self.assertEqual(account.institution.organization, 'USAA')
        self.assertEqual(account.number, '4111111111111111')


class TestGracefulFailures(TestCase):
    ''' Test that when fail_fast is False, failures are returned to the
    caller as warnings and discarded entries in the Statement class.
    '''
    def testDateFieldMissing(self):
        ''' The test file contains three transactions in a single
        statement.

        They fail due to:
        1) No date
        2) Empty date
        3) Invalid date
        '''
        ofx = OfxParser.parse(open_file('fail_nice/date_missing.ofx'), False)
        self.assertEqual(len(ofx.account.statement.transactions), 0)
        self.assertEqual(len(ofx.account.statement.discarded_entries), 3)
        self.assertEqual(len(ofx.account.statement.warnings), 0)

        # Test that it raises an error otherwise.
        self.assertRaises(OfxParserException, OfxParser.parse,
                          open_file('fail_nice/date_missing.ofx'))

    def testDecimalConversionError(self):
        ''' The test file contains a transaction that has a poorly formatted
        decimal number ($20). Test that we catch this.
        '''
        ofx = OfxParser.parse(open_file('fail_nice/decimal_error.ofx'), False)
        self.assertEqual(len(ofx.account.statement.transactions), 0)
        self.assertEqual(len(ofx.account.statement.discarded_entries), 1)

        # Test that it raises an error otherwise.
        self.assertRaises(OfxParserException, OfxParser.parse,
                          open_file('fail_nice/decimal_error.ofx'))

    def testEmptyBalance(self):
        ''' The test file contains empty or blank strings in the balance
        fields. Fail nicely on those.
        '''
        ofx = OfxParser.parse(open_file('fail_nice/empty_balance.ofx'), False)
        self.assertEqual(len(ofx.account.statement.transactions), 1)
        self.assertEqual(len(ofx.account.statement.discarded_entries), 0)
        self.assertFalse(hasattr(ofx.account.statement, 'balance'))
        self.assertFalse(hasattr(ofx.account.statement, 'available_balance'))

        # Test that it raises an error otherwise.
        self.assertRaises(OfxParserException, OfxParser.parse,
                          open_file('fail_nice/empty_balance.ofx'))

if __name__ == "__main__":
    import unittest
    unittest.main()
