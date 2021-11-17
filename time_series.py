from datetime import date, datetime, timedelta
from copy import deepcopy

class Schedule: # what Curve and ObjectSchedule have in common
	startDate= date(1900,1,1)
	def __init__(self, startDate, startValue):
		self.schedule= {}
		self.startDate= startDate
		self.schedule[startDate]= startValue
	def setValue(self, timestamp, value):
		self.schedule[timestamp]= value
	def getValue(self, timestamp):
		asOfDate= self.getMostRecentDate(timestamp)
		if asOfDate not in self.schedule:
			#raise Exception(timestamp.isoformat() + " not found in schedule")
			return None
		return self.schedule[asOfDate]
	def hasValue(self, timestamp):
		if not self.schedule:
			return False
		return (timestamp >= sorted(self.schedule)[0])
	def getMostRecentDate(self, asOfDate):
		if asOfDate in self.schedule:
			return asOfDate
		if not self.schedule:
			return Curve.startDate
		lastDate= Curve.startDate
		for tryDate in sorted(self.schedule):
			if tryDate > asOfDate:
				return lastDate
			lastDate = tryDate
		return tryDate

class Curve(Schedule): # a numeric value that changes day by day
	def __init__(self, startDate=Schedule.startDate, startValue=0):
		super().__init__(startDate, startValue)
	def incrementValue(self, asOfDate, increment):
		if (self.hasValue(asOfDate)):
			self.setValue(asOfDate, self.getValue(asOfDate) + increment)
		else:
			self.setValue(asOfDate, increment)
		for changeDate in self.schedule:
			if changeDate > asOfDate:
				self.setValue(changeDate, self.getValue(changeDate) + increment)
		
class ObjectSchedule(Schedule): # a time series of objects
	def __init__(self, start=datetime.now(), startValue={}):
		startDateTime= start if type(start) is datetime else datetime.combine(start,datetime.min.time())
		super().__init__(startDateTime, startValue)
	def setCurrentValue(self, value):
		asOfTime= datetime.now()
		self.setValue(asOfTime, value)
		return asOfTime
	def getCurrentValue(self):
		return self.getValue(datetime.now())
	def getOrCreateValue(self, asOfTime):
		if asOfTime in self.schedule:
			return self.schedule[asOfTime]
		previousValue= self.getValue(asOfTime)
		if previousValue:
			self.schedule[asOfTime]= deepcopy(previousValue)
			return self.schedule[asOfTime]
		return None
	def call(self, asOfTime, methodName, *args):
		obj= self.getValue(asOfTime)
		fn= getattr(obj, methodName)
		return fn(*args)
	def callCurrent(self, methodName, *args):
		return self.call(datetime.now(), methodName, *args)
