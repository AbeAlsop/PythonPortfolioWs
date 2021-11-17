from portfolio_model import *

portfolios= PortfolioStore()

#initial load
portfolio= portfolios.createPortfolio(date(2021,1,1))
portfolio.addInitialLot('AAPL', 1000, 125)
portfolio.addInitialLot('912828RR3', 10000, 1)
portfolio.addInitialLot('9128285J5', 25000, 1)
print(portfolio.getHoldingReport(date(2021,11,1)))

#security master
SecurityMaster.setCashSecurity('USD')
SecurityMaster.setSecurity('AAPL')
SecurityMaster.setSecurity('912828RR3', 'USD', 'TREASURY', 2.0, 2, date(2013,5,15), date(2022,11,15))
SecurityMaster.setSecurity('9128285J5', 'USD', 'TREASURY', 3.0, 2, date(2016,4,30), date(2025,10,31))
SecurityMaster.setSecurity('097023CY9', 'USD', 'BOEING CORP', 5.15, 2, date(2012,4,30), date(2021,10,31))
print(portfolio.getHoldingReport(date(2021,11,1)))

print()
print('BEGIN TRADING')
portfolio.applyTransaction(Transaction.createBuy(portfolio.accountId, 'CWAN', 1000, 18, date(2021,9,24), date(2021,9,28)))
portfolio.applyTransaction(Transaction.createSell(portfolio.accountId, 'AAPL', 500, 150, date(2021,11,8), date(2021,11,10)))
portfolio.applyTransaction(Transaction.createBuy(portfolio.accountId, '097023CY9', 20000, 1, date(2021,7,5), date(2021,7,7)))
SecurityMaster.setSecurity('CWAN', 'USD')
print(portfolio.getHoldingReport(date(2021,11,17)))
portfolio.snapshot()

print()
print('COUPONS & MATURITIES')
portfolio.postCashPayments(date(2021,11,17))
print(portfolio.getHoldingReport(date(2021,11,17)))
print(portfolio.getTransactionReport())

print()
print('RECONCILE TO CUSTODY')
reconDate= date(2021,11,19)
custodyPortfolio = Portfolio(reconDate, portfolio.accountId, 'CUSTODY')
portfolios.set(custodyPortfolio)
custodyPortfolio.addInitialLot('AAPL', 500, 125)
custodyPortfolio.addInitialLot('912828RR3', 10000)
custodyPortfolio.addInitialLot('9128285J5', 25000)
custodyPortfolio.addInitialLot('CWAN', 1000, 18)
custodyPortfolio.addInitialLot('USD', 58800)
print(portfolio.diffPositions(custodyPortfolio, reconDate))

#print()
#print("NEW TRANSACTION DOESN'T AFFECT LOCKED PERIOD")
portfolio.lock(date(2021,10,31))
portfolio.applyTransaction(Transaction.createBuy(portfolio.accountId, 'LP123', 50, 1000, date(2021,10,15), date(2021,10,17)))
print(portfolio.getLockedHoldingReport(date(2021,10,31)))
print(portfolio.getHoldingReport(date(2021,10,31)))


