from time_series import *

s2= ObjectSchedule(startValue=Curve(date(2021,2,1),50))
c= s2.getValue(datetime.now())
assert(c.getValue(date(2021,11,1))==50)

s3= ObjectSchedule(date(2021,1,1), Curve(date(2021,2,1),17))
s3.call(datetime.now(), 'incrementValue', date(2021,3,15), 5)
assert(len(s3.getCurrentValue().schedule)==2)
assert(s3.call(datetime.now(), 'getValue', date(2021,3,31))==22)
assert(s3.callCurrent('getValue', date(2021,2,15))==17)
