from flask import Flask
from flask import jsonify, make_response
from flask_restful import Api, Resource, reqparse, request
from portfolio_model import *

portfolios= PortfolioStore()
SecurityMaster.setCashSecurity('USD')

def getArguments(*fieldNames):
	parser = reqparse.RequestParser()
	for field in fieldNames:
		parser.add_argument(field)
	return parser.parse_args()

def strToDate(dateStr): # requires YYYYMMDD format
	return date(int(dateStr[:4]), int(dateStr[4:6]), int(dateStr[6:8]))
	
class PortfolioPostResource(Resource):
	def post(self):
		args = getArguments('startDate')
		portfolio = portfolios.createPortfolio(strToDate(args['startDate']))
		return make_response(jsonify(portfolio.accountId), 201)

class PortfolioResource(Resource):
	def get(self,id):
		if portfolios.contains(id):
			args = getArguments('date','source','preferLockdown')
			startDate= strToDate(args['date'])
			portfolio= portfolios.get(id, args['source'], startDate)
			report= portfolio.getLockedHoldingReport(startDate) if args['preferLockdown'] else portfolio.getHoldingReport(startDate)
			return make_response(jsonify(report), 200)
		else:
			return make_response("Not found", 404)
	def put(self,id):
		if portfolios.contains(id):
			args = getArguments('date','source')
			portfolio = portfolios.get(id, args['source'], strToDate(args['date']))
			req = request.get_json()
			holdings = req['holdings']
			for holding in holdings:
				portfolio.addInitialLot(holding['security'], holding['units'], holding['origPrice'] if 'origPrice' in holding else None)
			return make_response(jsonify(portfolios.get(id).getHoldingReport(strToDate(args['date']))), 201)
		else:
			return make_response("Not found", 404)

class ReconcileResource(Resource):
	def get(self,id):
		if portfolios.contains(id):
			args = getArguments('date', 'source1', 'source2')
			portfolio1= portfolios.get(id, args['source1'])
			portfolio2= portfolios.get(id, args['source2'])
			differences= portfolio1.diffPositions(portfolio2, strToDate(args['date']))
			return make_response(jsonify(differences), 200)
		else:
			return make_response("Not found", 404)

class SnapshotResource(Resource):
	def post(self,id):
		if portfolios.contains(id):
			args = getArguments('lockDate')
			if 'lockDate' in args:
				portfolios.get(id).lock(strToDate(args['lockDate']))
			else:
				portfolios.get(id).snapshot()
			return make_response("Success", 201)
		else:
			return make_response("Not found", 404)
		
class TransactionsResource(Resource):
	def get(self,id):
		if portfolios.contains(id):
			return make_response(jsonify(portfolios.get(id).getTransactionReport()), 200)
		else:
			return make_response("Not found", 404)
	def post(self,id): #currently just takes an integer and sets cash to that amount
		if portfolios.contains(id):
			portfolio = portfolios.get(id)
			req = request.get_json()
			transactions = req['transactions']
			for transaction in transactions:
				entryDate= strToDate(transaction['entryDate'])
				settleDate= strToDate(transaction['settleDate'])
				price= float(transaction['price'])
				units= float(transaction['units'])
				t = Transaction(transaction['type'], entryDate, settleDate, price, id, transaction['securityId'], units, -units * price)
				portfolio.applyTransaction(t)
			return make_response("Success", 201)
		else:
			return make_response("Not found", 404)

class CashFlowsResource(Resource):
	def post(self,id):
		if portfolios.contains(id):
			portfolios.get(id).postCashPayments(date.today())
			return make_response("Success", 201)
		else:
			return make_response("Not found", 404)

class SecurityResource(Resource):
	def post(self):
		req = request.get_json()
		securities = req['securities']
		for security in securities:
			securityId= security['id']
			currency= security['currency']
			type=security['type']
			couponRate=float(security['couponRate']) if 'couponRate' in security else 0.0
			couponFrequency=int(security['couponFrequency']) if 'couponFrequency' in security else None
			firstCouponDate=strToDate(security['firstCouponDate']) if 'firstCouponDate' in security else None
			maturityDate=strToDate(security['maturityDate']) if 'maturityDate' in security else None
			SecurityMaster.setSecurity(securityId, currency, type, couponRate, couponFrequency, firstCouponDate, maturityDate)
		return make_response("Success", 201)
	
def start_portfolio_ws():
	app = Flask(__name__)
	api = Api(app)
	api.add_resource(PortfolioPostResource, "/portfolio")
	api.add_resource(PortfolioResource, "/portfolio/<int:id>")
	api.add_resource(ReconcileResource, "/portfolio/<int:id>/reconcile")
	api.add_resource(SnapshotResource, "/portfolio/<int:id>/snapshot")
	api.add_resource(TransactionsResource, "/portfolio/<int:id>/transaction")
	api.add_resource(CashFlowsResource, "/portfolio/<int:id>/cashflows")
	api.add_resource(SecurityResource, "/security")
	app.run(debug=True)

start_portfolio_ws()