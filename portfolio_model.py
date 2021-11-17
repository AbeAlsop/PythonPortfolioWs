from time_series import *
from functools import reduce
import pandas as pd

class Transaction: 
	transactionId= 1
	def __init__(self, transactionType, entryDate, settleDate, price, accountId, securityId, unitsChange, cashChange):
		self.transactionId= Transaction.transactionId
		Transaction.transactionId += 1
		self.transactionType= transactionType
		self.entryDate= entryDate
		self.settleDate= settleDate
		self.price= price
		self.accountId= accountId
		self.securityId= securityId
		self.unitsChange= unitsChange
		self.cashChange= cashChange
		self.creationTime= datetime.now()
	def createBuy(accountId, securityId, units, price, entryDate, settleDate):
		return Transaction('BUY', entryDate, settleDate, price, accountId, securityId, units, -units * price)
	def createSell(accountId, securityId, units, price, entryDate, settleDate):
		return Transaction('SELL', entryDate, settleDate, price, accountId, securityId, -units, units * price)
	def createCashMovement(accountId, units, entryDate, type='CASH', securityId='USD'):
		return Transaction(type, entryDate, entryDate, 1.0, accountId, securityId, units, units)
	def getHeader():
		return ['Type','Security','Units','Price','Amount','Entry Date', 'Settle Date']
	def getRow(self):
		return [self.transactionType, self.securityId, self.unitsChange, self.price, self.cashChange, date.strftime(self.entryDate,"%Y-%m-%d"), date.strftime(self.settleDate,"%Y-%m-%d")]
	def opensNewLot(self):
		return (self.transactionType=='BUY')

class Holding(Curve):
	def __init__(self, securityId, accountId, asOfDate, units, origPrice):
		super().__init__(asOfDate, units)
		self.securityId=securityId
		self.accountId=accountId
		self.origPrice=origPrice
	def getUnits(self, asOfDate):
		if not self.hasValue(asOfDate):
			return 0
		return self.getValue(asOfDate)
	def exists(self, asOfDate):
		return self.getUnits(asOfDate) != 0
	def getHeader():
		return ['Account ID','Security','Units','Security Type','Currency','Original Cost','Coupon Rate','Maturity Date']
	def getRow(self, reportDate):
		maturityDate= date.strftime(SecurityMaster.getMaturityDateForSecurity(self.securityId),"%Y-%m-%d") if SecurityMaster.getMaturityDateForSecurity(self.securityId) else "N/A"
		return [self.accountId, self.securityId, self.getValue(reportDate), SecurityMaster.getTypeForSecurity(self.securityId), SecurityMaster.getCurrencyForSecurity(self.securityId), self.getValue(reportDate) * self.origPrice, SecurityMaster.getCouponRateForSecurity(self.securityId), maturityDate]
	
class Lot(Holding):
	lotId= 1
	entry= None #entry transaction
	transactionLinksByDate={} # date -> [links]
	def __init__(self, entry): 
		self.lotId= Lot.lotId
		Lot.lotId += 1
		if type(entry) is Transaction:
			super().__init__(entry.securityId, entry.accountId, entry.entryDate, entry.unitsChange, entry.price)
			self.entry= entry.transactionId
			self.addTransactionLink(TransactionLink(entry,self))
		elif type(entry) is Holding:
			super().__init__(entry.securityId, entry.accountId, entry.startDate, entry.getUnits(entry.startDate), entry.origPrice)
		else:
			raise Exception("Need Transaction or Holding to open a Lot")
	def addTransactionLink(self, link):
		date= link.transaction.entryDate
		if date in self.transactionLinksByDate:
			self.transactionLinksByDate[date].append(link)
		else:
			self.transactionLinksByDate[date]= [link]
	def applyExitTransaction(self, newTransaction): # returns number of units consumed
		unitsAvailable= self.getValue(newTransaction.entryDate)
		if unitsAvailable <= 0:
			return 0
		if unitsAvailable + newTransaction.unitsChange >= 0:
			self.incrementValue(newTransaction.entryDate, newTransaction.unitsChange)
			unitsUsed= newTransaction.unitsChange
		else:
			self.incrementValue(newTransaction.entryDate, -unitsAvailable)
			unitsUsed= -unitsAvailable
		self.addTransactionLink(TransactionLink(newTransaction, self, unitsUsed))
		return unitsUsed
	def applyCashPayment(self, cashTransaction):
		#overwrite existing payment of same type on same day if it exists
		if cashTransaction.entryDate in self.transactionLinksByDate:
			for index in range(len(self.transactionLinksByDate[cashTransaction.entryDate])):
				if self.transactionLinksByDate[cashTransaction.entryDate][index].transaction.transactionType==cashTransaction.transactionType:
					del self.transactionLinksByDate[cashTransaction.entryDate][index]
					break
		self.addTransactionLink(TransactionLink(cashTransaction, self))

class Cash(Holding):
	transactionsByDate={}
	def __init__(self, entry):
		if type(entry) is Transaction:
			super().__init__(SecurityMaster.getCurrencyForSecurity(entry.securityId), entry.accountId, entry.entryDate, entry.cashChange, 1.0)
			transactionsByDate= {entry.entryDate: [entry]}
		else:
			super().__init__(entry.securityId, entry.accountId, entry.startDate, entry.getUnits(entry.startDate), entry.origPrice)
	def applyTransaction(self, newTransaction):
		if newTransaction.entryDate not in self.transactionsByDate:
			self.transactionsByDate[newTransaction.entryDate] = [newTransaction]
		else:
			self.transactionsByDate[newTransaction.entryDate].append(newTransaction)
		self.incrementValue(newTransaction.entryDate, newTransaction.cashChange)
		return newTransaction.unitsChange

class TransactionLink:
	def __init__(self, transaction, lot, units=None):
		self.transaction= transaction
		self.lot= lot
		self.units= units if units else lot.getUnits(transaction.entryDate)

class PortfolioHistory(ObjectSchedule):
	def __init__(self, portfolio):
		super().__init__(datetime.now(), deepcopy(portfolio))
		self.lockdownSchedule= Schedule(portfolio.startDate, None)
	def snapshot(self, portfolio):
		return self.setCurrentValue(deepcopy(portfolio))
	def lockdown(self, periodEndDate):
		timestamp= self.getMostRecentDate(datetime.now())
		priorLockdown= self.lockdownSchedule.getMostRecentDate(periodEndDate)
		self.lockdownSchedule.setValue(priorLockdown, timestamp)
		self.lockdownSchedule.setValue(periodEndDate+timedelta(days=1), None)
	def getLockedPortfolio(self, asOfDate):
		lockTimestamp= self.lockdownSchedule.getValue(asOfDate)
		return self.getValue(lockTimestamp) if lockTimestamp else None
		
class Portfolio:
	nextAccountId= 1
	defaultSource= 'CW'
	def __init__(self, startDate, id=None, source=None):
		if not id:
			id= Portfolio.nextAccountId
			Portfolio.nextAccountId += 1
		self.accountId= id
		self.source= source if source else Portfolio.defaultSource
		self.startDate= startDate
		self.transactions= [] # TODO: remove duplication between this and transactions linked to holdings
		self.holdings= {} # securityId -> [holding]
		self.history= PortfolioHistory(self)
	def snapshot(self):
		return self.history.snapshot(self)
	def lock(self, periodEndDate):
		self.snapshot()
		self.history.lockdown(periodEndDate)
	def getPortfolioForReportDate(self, reportDate):
		lockedPortfolio= self.history.getLockedPortfolio(reportDate)
		return lockedPortfolio if lockedPortfolio else self
	def getPortfolioSnapshot(self, timestamp):
		historicPortfolio= self.history.getValue(timestamp)
		return historicPortfolio if historicPortfolio else self
	def getLockedHoldingReport(self, reportDate):
		lockedPortfolio= self.getPortfolioForReportDate(reportDate)
		return lockedPortfolio.getHoldingReport(reportDate)
	def getHoldingReport(self, reportDate):
		retValue= [Holding.getHeader()]
		for holdingsForSecurity in self.holdings.values():
			for holding in holdingsForSecurity:
				if holding.exists(reportDate):
					retValue.append(holding.getRow(reportDate))
		return retValue
	def getTransactionReport(self):
		return [Transaction.getHeader()] + list(map(Transaction.getRow, self.transactions))
	def addInitialLot(self, securityId, units, origPrice=None):
		if not origPrice:
			origPrice= 1.0
		if SecurityMaster.isCash(securityId):
			self.addHolding(Cash(Holding(securityId, self.accountId, self.startDate, units, 1.0)))
		else:
			self.addHolding(Lot(Holding(securityId, self.accountId, self.startDate, units, origPrice)))
	def addHolding(self, holding):
		if holding.securityId not in self.holdings:
			self.holdings[holding.securityId]= [holding]
		else:
			self.holdings[holding.securityId].append(holding)
	def applyTransaction(self, transaction):
		self.transactions.append(transaction)
		if not SecurityMaster.isCash(transaction.securityId):
			#do lot inventory
			if transaction.securityId not in self.holdings:
				self.holdings[transaction.securityId]= [Lot(transaction)]
			elif transaction.opensNewLot():
				self.holdings[transaction.securityId].append(Lot(transaction))
			else:
				unitsRemaining= transaction.unitsChange
				for holding in self.holdings[transaction.securityId]:
					if type(holding) is Lot and holding.exists(transaction.entryDate):
						unitsUsed = holding.applyExitTransaction(transaction)
						unitsRemaining -= unitsUsed
						if unitsRemaining <= 0:
							break
				if unitsRemaining > 0:
					plugTransaction= deepcopy(transaction)
					plugTransaction.units = unitsRemaining
					self.holdings[transaction.securityId].append(Lot(plugTransaction))
				#holding.bookValue *= 1.0 + (transaction.getUnitChange() / holding.units)
		#cash units
		cashSecurity= SecurityMaster.getCurrencyForSecurity(transaction.securityId)
		if cashSecurity not in self.holdings:
			newLot= Cash(transaction)
			self.holdings[cashSecurity]= [newLot]
		else:
			cashPosition= self.holdings[cashSecurity][0]
			cashPosition.applyTransaction(transaction)
	def postCashPayments(self, endDate):
		securityIds = [s for s in self.holdings if SecurityMaster.hasCoupon(s)]
		for securityId in securityIds:
			couponDates= SecurityMaster.getCouponDatesForSecurity(securityId)
			maturityDate= SecurityMaster.getMaturityDateForSecurity(securityId)
			for holding in self.holdings[securityId]:
				if type(holding) is Lot:
					for date in couponDates:
						if date <= endDate and holding.exists(date):
							newCpn= Transaction.createCashMovement(holding.accountId, holding.getUnits(date)*SecurityMaster.getCouponRateForSecurity(securityId)/100, date, 'CPN', SecurityMaster.getCurrencyForSecurity(securityId))
							holding.applyCashPayment(newCpn)
							self.applyTransaction(newCpn)		
					if maturityDate <= endDate and holding.exists(maturityDate):
						units= holding.getUnits(maturityDate)
						newMaturity= Transaction('MAT', maturityDate, maturityDate, 1.0, holding.accountId, securityId, -units, units)
						self.applyTransaction(newMaturity)
	def sumUnits(self, security, asOfDate):
		if security in self.holdings:
			return reduce(lambda x,y:x+y, map(lambda holding:holding.getValue(asOfDate), self.holdings[security]))
		else:
			return 0
	def diffPositions(self, other, asOfDate):
		retValue= []
		for security in set(self.holdings.keys()).union(set(other.holdings.keys())):
			selfUnits= self.sumUnits(security, asOfDate)
			otherUnits= other.sumUnits(security, asOfDate)
			if (selfUnits != otherUnits):
				retValue.append({'security':security, self.source:selfUnits, other.source:otherUnits})
		return retValue
	
class PortfolioStore:
	def __init__(self):
		self.portfolios = {} # accountId => source => portfolio
	def createPortfolio(self, startDate):
		p= Portfolio(startDate)
		self.set(p)
		return p
	def set(self, portfolio):
		if portfolio.accountId not in self.portfolios:
			self.portfolios[portfolio.accountId]= {}
		source= portfolio.source
		self.portfolios[portfolio.accountId][source]= portfolio
	def contains(self, id):
		return id in self.portfolios
	def get(self, id, source=None, startDate=None):
		if id not in self.portfolios:
			return None
		if not source:
			source= Portfolio.defaultSource
		if source not in self.portfolios[id] and startDate:
			#if it doesn't exist and startDate is provided, then create a new one
			newPortfolio= Portfolio(startDate, id, source)
			self.set(newPortfolio)
		return self.portfolios[id][source]

class SecurityMaster:
	securities= {}
	prices= {}
	def setSecurity(securityId, currency='USD', type='EQUITY', couponRate=0, couponFrequency=None, firstCouponDate=None, maturityDate=None):
		SecurityMaster.securities[securityId]= {'currency':currency, 'type':type, 'couponRate':couponRate, 'couponFrequency':couponFrequency, 'firstCouponDate':firstCouponDate, 'maturityDate':maturityDate}
	def setCashSecurity(securityId):
		SecurityMaster.setSecurity(securityId, securityId, 'CCY')
	def lookupValue(securityId, key, default=None):
		if securityId in SecurityMaster.securities:
			return SecurityMaster.securities[securityId][key]
		else:
			return default
	def getCurrencyForSecurity(securityId):
		return SecurityMaster.lookupValue(securityId, 'currency', 'USD')
	def isCash(securityId):
		return securityId==SecurityMaster.lookupValue(securityId, 'currency')
	def hasCoupon(securityId):
		return SecurityMaster.getCouponRateForSecurity(securityId) != 0
	def getTypeForSecurity(securityId):
		return SecurityMaster.lookupValue(securityId, 'type', 'UNKNOWN')
	def getFirstCouponDateForSecurity(securityId):
		return SecurityMaster.lookupValue(securityId, 'firstCouponDate')
	def getMaturityDateForSecurity(securityId):
		return SecurityMaster.lookupValue(securityId, 'maturityDate')
	def getCouponRateForSecurity(securityId):
		return SecurityMaster.lookupValue(securityId, 'couponRate', 0)
	def getCouponFrequencyPerYear(securityId):
		return SecurityMaster.lookupValue(securityId, 'couponFrequency')
	def getPriceForSecurity(securityId, asOfDate):
		if securityId in SecurityMaster.prices:
			return SecurityMaster.prices['securityId'].getValue(asOfDate)
		else:
			return None
	def getCouponDatesForSecurity(securityId):
		if SecurityMaster.getCouponRateForSecurity(securityId):
			retVal= []
			currentDate= SecurityMaster.getFirstCouponDateForSecurity(securityId)
			endDate= SecurityMaster.getMaturityDateForSecurity(securityId)
			cpdPeriod= pd.DateOffset(months= (12 / SecurityMaster.getCouponFrequencyPerYear(securityId)))
			while currentDate <= endDate:
				retVal.append(currentDate)
				currentDate = (currentDate + pd.DateOffset(days=1) + cpdPeriod + pd.DateOffset(days=-1)).date()
			return retVal
		else:
			return []
