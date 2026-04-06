const grpc = require("@grpc/grpc-js");
const validator = require("validator");
const xssFilters = require("xss-filters");

const log = require("../util-log");
const state = require("./state");
const config = require("../util-config");
const protoLoader = require("@grpc/proto-loader");
const {getProtoFile} = require("./defineProtofile");
const grpcClients = require("./clientsActivasion");



const responseHandler = require("../helpers/responseHandler");
const {cancelTransaction} = require("../grpc/transfers/cancelTransaction");
const {getServiceProvidersByPropvalue} = require("./transfers/getServiceProvidersByPropvalue");

const {makeSwiftTransferRequest_v2} = require("./transfers/make/makeSwiftTransferRequest");
const {makeOtherBankTransferRequest_v2} = require("./transfers/make/makeOtherBankTransferRequest");
const {makeBankClientTransferRequest_v2} = require("./transfers/make/makeBankClientTransferRequest");
const {makeOwnAccountsTransferRequest_v2} = require("./transfers/make/ownAccountsTransferRequest");
const {makeDepositReplenishmentRequest_v2} = require("./transfers/make/makeDepositReplenishmentRequest");


const {makeIpcCardTransferRequest_v2} = require("./transfers/make/makeIpcCardTransfer_Elcard");

const {paymentController} = require("../grpc/payments/payment-controller");
const {sendOtpBySms} = require("./utilities/sendOtpBySms");

const {shopOperationRouter} = require("./shop/shopOperationRouter");
const {shopTxnOperationRouter} = require("./shop/shopTxnOperationRouter_v2");

const { makeWalletReplenishmentRequest } = require("./transfers/make/makeWalletReplenishmentRequest");
const { confirmOperation_v2 } = require("./transfers/confirm/operation-confirmation-controller");
const { createConfirmOperationTask } = require("./transfers/confirm/create-operation-confirmation_corp");
const { confirmOperation__corp } = require("./transfers/confirm/operation-confirmation-controller_corp");

const { sendOtpBySms__corp_confirm } = require("./utilities/sendOtpBySms__corp_multilevel_confirm");
const { transactionController_bulk } = require("./transfers/make/bulk/file_upload-controller");
const { selectedBatchController } = require("./transfers/make/bulk/selected_txns-controller");
const { sendTransactionToProcessingCorp } = require("./transfers/confirm/send-transaction-to-processing-corp");
const { sendTransactionsToProcessingCorp } = require("./transfers/confirm/send-transactions-to-processing-corp");
const { deleteTransactionById } = require("./transfers/deleteTransactionById");
const { getFileByTxnId } = require("./transfers/getFileByTxnId");
const { digitalLoanMakeRepaymentController } = require("./transfers/make/digitalLoanMakeRepaymentController");


//MTS
const {moneyTransferController} = require("./mts/money-transfer-controller");

// QR 
const {getQrPaymentCredentials} = require("./elqr/getQrPaymentCredentials");
const {qrPaymentController} = require("./elqr/makeQrPayment");


// VISA

const {visa2visaOctController} = require("./visa-2-visa/makeVisa2VisaOct");
const {visa2visaAftController} = require("./visa-2-visa/makeVisa2VisaAft");
const {showAdditionalFieldsByPhoneOrCardPan} = require("./visa-2-visa/showAdditionalFieldsByPhoneOrCardPan");
const { makeDistributionOperations } = require("./distribution/makeDistributionOperations");
const {moneyExpressOutController} = require("./money-express/make-money-express-out");
const {transferInquiryController} = require("./mts/transfer-inquiry-controller");
const {mastercard2mastercardController} = require("./mastercard/mastercard2mastercard");
const {accountValidateController} = require("./mts/acc-validation-controller");
const transfer_api_protofile_name = "webTransferApi.proto";
let packageDefinition = null;
let grpcServicePackage = null;
let grpcServer = null;

const ALLOWED_HEADER_PARAMS = [
	{name: "sessionKey", 					type: "string",  maxLen: 32, required: true},
	{name: "refId", 						type: "string",  maxLen: 80, required: true},
	{name: "userId", 						type: "integer", maxLen: 64, required: true},
	{name: "status", 						type: "string",  maxLen: 64, required: false},
	{name: "sessionId", 					type: "string",  maxLen: 64, required: true},
	{name: "customerNo", 					type: "string",  maxLen: 64, required: true},
	{name: "userLocale", 					type: "string",  maxLen: 64, required: false},
	{name: "userPhoneNumber", 				type: "string",  maxLen: 64, required: false},
	{name: "userOtpDelivery", 				type: "string",  maxLen: 64, required: false},
	{name: "lastPasswordChangeTimestamp", 	type: "string",  maxLen: 64, required: false},
	{name: "customerIndCorp", 				type: "string",  maxLen: 64, required: true},
	{name: "username", 						type: "string",  maxLen: 64, required: false},
	{name: "userBranch", 					type: "string",  maxLen: 64, required: false},
	{name: "userEmail", 					type: "string",  maxLen: 64, required: false},
	{name: "isUserActive", 					type: "boolean", required: false},
	{name: "isUserReadOnly", 				type: "boolean", required: true},
	{name: "isCustomerReadOnly", 			type: "boolean", required: true},
	{name: "isJointAccount", 				type: "boolean", required: false},
	{name: "isTrusted", 					type: "boolean", required: false},
	{name: "isMaker", 						type: "boolean", required: false},
	{name: "isChecker", 					type: "boolean", required: false},
];

exports.init = async function () {
	grpcClients.init();
	await exports.start();
};

exports.methodObjects = {
	MAKE_OWN_ACCOUNTS_TRANSFER: {
		funcName: "makeOwnAccountsTransferRequest_v2",
		func: makeOwnAccountsTransferRequest_v2,
		metric: "grpc-ownAccountTransfer",
		code: state.TRANSFERS_CODES.MAKE_OWN_ACCOUNTS_TRANSFER,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "valueDate", type: "string", maxLen: 32,  minLen: 1, required: false},
			{name: "accountIdDebit", type: "integer", maxLen: 10, required: true},
			{name: "accountIdCredit", type: "integer", maxLen: 10, required: true},
			{name: "amountDebit", type: "string", maxLen: 32, required: true},
			{name: "exchangeDealId", type: "integer", maxLen: 32, required: false},
			{name: "valueTime", type: "string", maxLen: 32, minLen: 1, required: false},
			{name: "theirRefNo", type: "string", maxLen: 32, minLen: 0, required: false},
			{name: "knp", type: "string", maxLen: 32, minLen: 0, required: false},
			{name: "paymentPurpose", type: "string", maxLen: 200, minLen: 0, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	MAKE_SWIFT_TRANSFER: {
		funcName: "makeSwiftTransferRequest_v2",
		func: makeSwiftTransferRequest_v2,
		metric: "grpc-swiftTransferRequest",
		code: state.TRANSFERS_CODES.MAKE_SWIFT_OPERATION,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, minLen: 16, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 64,  minLen: 1,  required: true},
			{name: "amountDebit", type: "string", maxLen: 20, minLen: 1, required: true},
			{name: "valueDate", type: "string", maxLen: 32,  minLen: 1, required: true},
			{name: "transferCcy", type: "string", maxLen: 3,  minLen: 3, required: true},
			{name: "recipientAddress", type: "string", maxLen: 70, minLen: 4, required: true},
			{name: "recipientName", type: "string", maxLen: 70, minLen: 4, required: true},
			{name: "recipientBankSwift", type: "string", maxLen: 11, minLen: 1, required: true},
			{name: "recipientBankBranch", type: "string", maxLen: 70, minLen: 1, required: false},
			{name: "recipientAccNo", type: "string", maxLen: 35, required: true},
			{name: "intermediaryBankSwift", type: "string", maxLen: 11, required: false},
			{name: "transferPurposeText", type: "string", maxLen: 200, minLen: 4, required: true},
			{name: "commissionType", type: "string", maxLen: 7, minLen: 3, required: true},
			{name: "documentNumber", type: "string", maxLen: 10, minLen: 1, required: false},
			{name: "commissionAccountId", type: "string", maxLen: 32, minLen: 1, required: false},
			{name: "corAccNo", type: "string", maxLen: 20,  minLen: 1, required: false},
			{name: "voCode", type: "string", maxLen: 8, minLen: 5, required: false},
			{name: "inn", type: "string", maxLen: 16, minLen: 9, required: false},
			{name: "kpp", type: "string", maxLen: 10, minLen: 0, required: false},
			{name: "bin", type: "string", maxLen: 16, minLen: 10, required: false},
			{name: "kbe", type: "string", maxLen: 5, minLen: 1, required: false},
			{name: "knp", type: "string", maxLen: 7, minLen: 1, required: false},
			{name: "theirRefNo", type: "string", maxLen: 32, minLen: 0, required: false},
			{name: "valueTime", type: "string", maxLen: 10, minLen: 1, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
			{name: "files", type: "array", minLen: 1, required: false},
		]
	},
	MAKE_OTHER_BANK_TRANSFER: {
		funcName: "makeOtherBankTransferRequest_v2",
		func: makeOtherBankTransferRequest_v2,
		metric: "grpc-makeOtherBankTransferRequest",
		code: state.TRANSFERS_CODES.MAKE_OTHER_BANK_TRANSFER,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, minLen: 16, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 64,  minLen: 1,  required: true},
			{name: "transferClearingGross", type: "string", maxLen: 1,  minLen: 1,  required: true},
			{name: "valueDate", type: "string", maxLen: 32,  minLen: 1, required: true},
			{name: "recipientName", type: "string", maxLen: 140,  minLen: 4,  required: true},
			{name: "recipientBankBic", type: "string", maxLen: 32,  minLen: 1,  required: true},
			{name: "accountCreditNumber", type: "string", maxLen: 16, minLen: 16, required: true},
			{name: "transferPurposeText", type: "string", maxLen: 140,  minLen: 4,  required: true},
			{name: "knp", type: "string", maxLen: 32,  minLen: 1,  required: true},
			{name: "amountCredit", type: "string", maxLen: 32,  minLen: 1,  required: true},
			{name: "valueTime", type: "string", maxLen: 10, minLen: 1, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
			{name: "theirRefNo", type: "string", maxLen: 32, minLen: 0, required: false},
			{name: "receiverInn", type: "string", maxLen: 14, minLen: 14, required: false},
		]
	},
	MAKE_BANK_CLIENT_TRANSFER: {
		funcName: "makeBankClientTransferRequest_v2",
		func: makeBankClientTransferRequest_v2,
		metric: "grpc-makeBankClientTransferRequest",
		code: state.TRANSFERS_CODES.MAKE_BANK_CLIENT_TRANSFER,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, minLen: 10,required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 10, minLen: 1, required: true},
			{name: "accountCreditPropValue", type: "string", maxLen: 32, minLen: 1, required: true},
			{name: "accountCreditPropType", type: "string", maxLen: 32, minLen: 4, required: true},
			{name: "paymentPurpose", type: "string", maxLen: 200, minLen: 0, required: false},
			{name: "amountDebit", type: "string", maxLen: 32, minLen: 1, required: true},
			{name: "valueDate", type: "string", maxLen: 32, minLen: 1, required: false},
			{name: "knp", type: "string", maxLen: 32,  minLen: 1,  required: false},
			{name: "theirRefNo", type: "string", maxLen: 32, minLen: 0, required: false},
			{name: "valueDate", type: "string", maxLen: 32,  minLen: 1, required: false},
			{name: "valueTime", type: "string", maxLen: 10, minLen: 1, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
			{name: "qrPayment", type: "boolean", required: false },
			{name: "qrAccountChangeable", type: "boolean", required: false },
			{name: "qrComment", type: "string", maxLen: 300, required: false },
			{ name: "qrServiceName", type: "string", maxLen: 300, required: false },
			{name: "qrServiceId", type: "string", maxLen: 300, required: false },
			{name: "clientType", type: "string", maxLen: 300, required: false },
			{name: "qrVersion", type: "string", maxLen: 300, required: false },
			{name: "qrType", type: "string", maxLen: 300, required: false },
			{name: "qrMerchantProviderId", type: "string", maxLen: 300, required: false },
			{name: "qrMerchantId", type: "string", maxLen: 300, required: false },
			{name: "qrServiceId", type: "string", maxLen: 300, required: false },
			{name: "qrAccount", type: "string", maxLen: 300, required: false },
			{name: "qrMcc", type: "string", maxLen: 300, required: false },
			{name: "qrCcy", type: "string", maxLen: 300, required: false },
			{name: "qrTransactionId", type: "string", maxLen: 300, required: false },
			{name: "qrControlSum", type: "string", maxLen: 300, required: false },
		]
	},
	MAKE_IPC_CARD_TRANSFER: {
		funcName: "makeIpcCardTransferRequest_v2",
		func: makeIpcCardTransferRequest_v2,
		metric: "grpc-makeIpcCardTransferRequest_v2",
		code: state.TRANSFERS_CODES.MAKE_IPC_CARD_TRANSFER,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "amountCredit", type: "string", maxLen: 32, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "accountCreditCardPan", type: "string", maxLen: 16, minLen: 16, required: true},
			{name: "paymentPurpose", type: "string", maxLen: 140, minLen: 0, required: false},
			{name: "theirRefNo", type: "string", maxLen: 32, minLen: 0, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	CONFIRM_TRANSFER: {
		funcName: "confirmOperation_v2",
		func: confirmOperation_v2,
		metric: "grpc-confirmOperation_v2",
		code: state.TRANSFERS_CODES.CONFIRM_TRANSFER,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "otp", type: "string", maxLen: 9, required: false}
		]
	},
	SEND_OTP_BY_SMS: {
		funcName: "sendOtpBySms",
		func: sendOtpBySms,
		metric: "grpc-sendOtpBySms",
		code: state.TRANSFERS_CODES.SEND_OTP_BY_SMS,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
		]
	},
	SEND_OTP_BY_SMS_CORP_USERS: {
		funcName: "sendOtpBySms__corp_confirm",
		func: sendOtpBySms__corp_confirm,
		metric: "grpc-sendOtpBySms__corp_confirm",
		code: state.TRANSFERS_CODES.SEND_OTP_BY_SMS_CORP_USERS,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
		]
	},
	MAKE_DEPOSIT: {
		funcName: "makeDepositReplenishmentRequest_v2",
		func: makeDepositReplenishmentRequest_v2,
		metric: "grpc-sendOtpBySms",
		code: state.TRANSFERS_CODES.MAKE_DEPOSIT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "depositId", type: "integer", maxLen: 20, required: true},
			{name: "amountDebit", type: "string", maxLen: 64, required: true},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	MAKE_SHOP_OPERATION: {
		funcName: "makeShopRequest",
		func: shopOperationRouter,
		metric: "grpc-make-shop-request",
		code: state.MAKE_SHOP_OPERATION,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: false},
			{name: "productType", type: "string", maxLen: 30, required: true},
			{name: "data", type: "object",  required: false}
		]
	},
	MAKE_TXN_SHOP_OPERATION: {
		funcName: "makeTxnShopRequest",
		func: shopTxnOperationRouter,
		metric: "grpc-make-txn-shop-request",
		code: state.MAKE_TXN_SHOP_OPERATION,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "productType", type: "string", maxLen: 30, required: true},
			{name: "data", type: "object",  required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},

	// payments
	MAKE_GENERIC_PAYMENT_V2: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-payment-handler",
		code: state.PAYMENT_TYPE.GENERIC_PAYMENT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 45, required: true},
			{name: "propValue", type: "string", maxLen: 45, required: true},
			{name: "amountCredit", type: "string", maxLen: 32, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 32, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "theirRefNo", type: "string", maxLen: 32, minLen: 0, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	MAKE_MOBILE_PAYMENT_V2: {
		funcName: "mobilePaymentHandler",
		func: paymentController,
		metric: "grpc-mobile-payment-handler",
		code: state.PAYMENT_TYPE.MOBILE_PAYMENT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 45, required: true},
			{name: "recipientNumber", type: "string", maxLen: 10, required: true},
			{name: "amountCredit", type: "string", maxLen: 10, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 32, required: false},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	MAKE_LAND_TAX_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		code: state.PAYMENT_TYPE.MAKE_LAND_TAX_PAYMENT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "account", type: "string", maxLen: 14, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "regionCode", type: "string", maxLen: 16, required: true},
			{name: "districtCode", type: "string", maxLen: 16, required: true},
			{name: "okmotCode", type: "string", maxLen: 32, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},

	MAKE_PATENT_TAX_VOLUNTARY: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		code: state.PAYMENT_TYPE.MAKE_PATENT_TAX_VOLUNTARY,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "account", type: "string", maxLen: 14, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "regionCode", type: "string", maxLen: 16, required: true},
			{name: "districtCode", type: "string", maxLen: 16, required: true},
			{name: "okmotCode", type: "string", maxLen: 32, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	MAKE_GENERIC_SINGLE_PAYMENT_V2: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		code: state.PAYMENT_TYPE.MAKE_GENERIC_SINGLE_PAYMENT,
		headerParams: [
			{name: "sessionKey", type: "string", maxLen: 60, required: true},
			{name: "refId", type: "string", maxLen: 60, required: true}
		],
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "propValue", type: "string", maxLen: 14, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	MAKE_PATENT_TAX_MANDATORY: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		code: state.PAYMENT_TYPE.MAKE_PATENT_TAX_MANDATORY,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "account", type: "string", maxLen: 14, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "regionCode", type: "string", maxLen: 16, required: true},
			{name: "districtCode", type: "string", maxLen: 16, required: true},
			{name: "okmotCode", type: "string", maxLen: 32, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},

	MAKE_TRANSPORT_TAX_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		code: state.PAYMENT_TYPE.MAKE_LAND_TAX_PAYMENT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "account", type: "string", maxLen: 14, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "regionCode", type: "string", maxLen: 16, required: true},
			{name: "districtCode", type: "string", maxLen: 16, required: true},
			{name: "okmotCode", type: "string", maxLen: 32, required: false},
			{name: "vehicleNumber", type: "string", maxLen: 32, required: true},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},

	MAKE_IMMOVABLE_TAX_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		code: state.PAYMENT_TYPE.MAKE_IMMOVABLE_TAX_PAYMENT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "account", type: "string", maxLen: 14, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "regionCode", type: "string", maxLen: 16, required: true},
			{name: "districtCode", type: "string", maxLen: 16, required: true},
			{name: "okmotCode", type: "string", maxLen: 32, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},

	MAKE_EMPLOYEE_INCOME_TAX: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		code: state.PAYMENT_TYPE.MAKE_EMPLOYEE_INCOME_TAX,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "account", type: "string", maxLen: 14, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "regionCode", type: "string", maxLen: 16, required: true},
			{name: "districtCode", type: "string", maxLen: 16, required: true},
			{name: "okmotCode", type: "string", maxLen: 32, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},


	MAKE_JANY_KITEP_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		code: state.PAYMENT_TYPE.MAKE_JANY_KITEP_PAYMENT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "propValue", type: "string", maxLen: 14, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "schoolYear", type: "string", maxLen: 9, required: true},
			{name: "fullName", type: "string", maxLen: 100, required: true},
			{name: "grade", type: "string", maxLen: 10, minLen: 1, required: true},
			{name: "letter", type: "string", maxLen: 1, minLen:1, required: true},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	CONFIRM_PAYMENT: {
		funcName: "confirmOperation_v2",
		func: confirmOperation_v2,
		metric: "grpc-confirmOperation_v2",
		code: state.PAYMENT_TYPE.CONFIRM_PAYMENT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "otp", type: "string", maxLen: 9, required: false}
		]
	},
	MAKE_WALLET_REPLENISHMENT: {
		funcName: "makeWalletReplenishmentRequest",
		func: makeWalletReplenishmentRequest,
		metric: "grpc-makeWalletReplenishmentRequest",
		code: state.TRANSFERS_CODES.MAKE_WALLET_REPLENISHMENT,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "walletId", type: "integer", maxLen: 20, required: true},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
		]
	},
	GET_SERVICE_PROVIDERS_BY_PROPVALUE: {
		funcName: "getServiceProvidersByPropvalue",
		func: getServiceProvidersByPropvalue,
		metric: "grpc-getServiceProvidersByPropvalue",
		code:state.TRANSFERS_CODES.GET_SERVICE_PROVIDERS_BY_PROPVALUE,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "propValue", type: "string", maxLen: 300, required: true},
		]
	},
	CANCEL_TRANSACTION: {
		funcName: "cancelTransaction",
		func: cancelTransaction,
		metric: "grpc-cancelTransaction",
		code:state.TRANSFERS_CODES.CANCEL_TRANSACTION,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "txnId", type: "integer", maxLen: 64, required: true},
		]
	},

	// CORPORATE
	CREATE_CONFIRM_OPERATION: {
		funcName: "createConfirmOperationTask",
		func: createConfirmOperationTask,
		metric: "grpc-createConfirmOperationTask",
		code:state.TRANSFERS_CODES.CREATE_CONFIRM_OPERATION,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "txnsArray", type: "array", minLen: 1, required: true},
			{name: "confirmStatus", type: "string", maxLen: 1, required: true},
		]
	},
	CONFIRM_CONFIRM_OPERATION: {
		funcName: "createConfirmOperationTask",
		func: confirmOperation__corp,
		metric: "grpc-createConfirmOperationTask",
		code:state.TRANSFERS_CODES.CONFIRM_CONFIRM_OPERATION,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", minLen: 1, required: true},
			{name: "otp", type: "string", maxLen: 9, required: false}
		]
	},
	SEND_OTP_BY_SMS_MULT_CONFIRM: {
		funcName: "sendOtpBySms",
		func: sendOtpBySms,
		metric: "grpc-sendOtpBySms",
		code: state.TRANSFERS_CODES.SEND_OTP_BY_SMS_MULT_CONFIRM,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
		]
	},
	SEND_TXN_TO_PROCESSING_CORP: {
		funcName: "sendTransactionToProcessingCorp",
		func: sendTransactionToProcessingCorp,
		metric: "grpc-sendTransactionToProcessingCorp",
		code: state.TRANSFERS_CODES.SEND_TXN_TO_PROCESSING_CORP,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "txnId", type: "integer", maxLen: 64, required: true},
		]
	},
	SEND_TXNS_TO_PROCESSING_CORP: {
		funcName: "sendTransactionыToProcessingCorp",
		func: sendTransactionsToProcessingCorp,
		metric: "grpc-sendTransactionsToProcessingCorp",
		code: state.TRANSFERS_CODES.SEND_TXNS_TO_PROCESSING_CORP,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "txnIdsArr", type: "array", minLen: 1, required: true},
		]
	},
	UPLOAD_BATCH_FILE: {
		funcName: "transactionController_bulk",
		func: transactionController_bulk,
		metric: "grpc-transactionController_bulk",
		code: state.TRANSFERS_CODES.UPLOAD_BATCH_FILE,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "files", type: "array", minLen: 1, required: true},
			{name: "extension", type: "string", minLen: 1, required: true},
			{name: "type", type: "string", minLen: 1, required: true},
			{name: "valueTime", type: "string", maxLen: 10, minLen: 1, required: false},
			{name: "valueDate", type: "string", maxLen: 32,  minLen: 1, required: false},
		]
	},
	SELECT_BATCH_TXNS: {
		funcName: "selectedBatchController",
		func: selectedBatchController,
		metric: "grpc-transactionController_bulk",
		code: state.TRANSFERS_CODES.SELECT_BATCH_TXNS,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "type", type: "string", maxLen: 64, required: true},
			{name: "transactions", type: "array", minLen: 1, required: true},
			// {name: "paramType", type: "string", minLen: 1, required: false},
		]
	},
	//MTS
	MAKE_MONEY_TRANSFER: {
		funcName: "moneyTransferController",
		func: moneyTransferController,
		metric: "grpc-moneyTransferController",
		code: state.TRANSFERS_CODES.MONEY_TRANSFER,
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "moneyTransferType", type: "string", maxLen: 64, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: false},
			{name: "amountCredit", type: "string", maxLen: 20, required: false},
			{name: "creditCcy", type: "string", maxLen: 20, required: false},
			{name: "destinationCcy", type: "string", maxLen: 20, required: false},
			{name: "debitCcy", type: "string", maxLen: 20, required: false},
			{name: "propValue", type: "string", maxLen: 50, required: true},
			{name: "phoneNumber", type: "string", maxLen: 50, required: false},
			{name: "creditCcyCode", type: "string", maxLen: 5, required: false},
			{name: "recipientBankTitle", type: "string",required: false},
			{name: "recipientMobileWalletTitle", type: "string",required: false},
			{name: "recipientCountryCode", type: "string", maxLen: 5, required: false},
			{name: "recipientCountryName", type: "object", required: false},
			{name: "recipientStateCode", type: "string", maxLen: 10, minLen: 1, required: false},
			{name: "recipientStateTitle", type: "string",required: false},
			{name: "recipientCityTitle", type: "string",required: false},
			{name: "recipientCityCode", type: "integer", maxLen: 20, required: false},
			{name: "recipientCityName", type: "object",required: false},
			{name: "recipientFirstName", type: "string", maxLen: 50, minLen: 2, required: false},
			{name: "recipientLastName", type: "string", maxLen: 50, minLen: 2, required: false},
			{name: "recipientMiddleName", type: "string", maxLen: 50, minLen: 2, required: false},
			{name: "propType", type: "string", maxLen: 12, required: false},
			{name: "transferPurposeText", type: "string", maxLen: 50, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
			{name: "accountIdCredit", type: "integer", maxLen: 32, required: false},
			{name: "marketingFlag", type: "boolean", required: false},
			{name: "transferMethodId", type: "integer", maxLen: 10, minLen: 1, required: false},
			{name: "recipientPartnerLocId", type: "integer", maxLen: 10, minLen: 1, required: false},
			{name: "recipientPartnerId", type: "integer", maxLen: 10, minLen: 1, required: false},
			{name: "relationWithRecipient", type: "string", maxLen: 10, minLen: 1, required: false},
			{name: "transferReasonId", type: "integer", maxLen: 10, minLen: 1, required: false},
		]
	},
	//MTS
	TRANSFER_INQUIRY: {
		funcName: "transferInquiryController",
		func: transferInquiryController,
		metric: "grpc-transferInquiryController",
		code: "TRANSFER_INQUIRY",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "moneyTransferType", type: "string", maxLen: 64, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "creditCcy", type: "string", maxLen: 20, required: false},
			{name: "creditCcyCode", type: "string", maxLen: 5, required: true},
			{name: "recipientCountryCode", type: "string", maxLen: 5, required: true},
		]
	},
	ACCOUNT_VALIDATE: {
		funcName: "accountValidateController",
		func: accountValidateController,
		metric: "grpc-accountValidateController",
		code: "TRANSFER_INQUIRY",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "moneyTransferType", type: "string", maxLen: 64, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "creditCcy", type: "string", maxLen: 20, required: false},
			{name: "creditCcyCode", type: "string", maxLen: 5, required: true},
			{name: "recipientCountryCode", type: "string", maxLen: 5, required: true},
			{name: "propValue", type: "string", maxLen: 50, required: true},
			{name: "recipientFirstName", type: "string", maxLen: 50, minLen: 2, required: false},
			{name: "recipientLastName", type: "string", maxLen: 50, minLen: 2, required: false},
			{name: "recipientMiddleName", type: "string", maxLen: 50, minLen: 2, required: false},
			{name: "transferPurposeText", type: "string", maxLen: 50, required: false},
		]
	},
	TRANSACTION_DELETE_BY_ID: {
		funcName: "deleteTransactionById",
		func: deleteTransactionById,
		metric: "grpc-delete-transaction-by-id",
		code: "TRANSACTION_DELETE",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "txnId", type: "integer", maxLen: 32, required: true },
		]
	},
	GET_FILE_BY_TXN_ID: {
		funcName: "getFileByTxnId",
		func: getFileByTxnId,
		metric: "grpc-get-file-by-txn-id",
		code: "TRANSACTION_DELETE",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "txnId", type: "integer", maxLen: 32, required: true },
		]
	},
	GET_QR_PAYMENT_CREDENTIALS: {
		funcName: "getQrPaymentCredentials",
		func: getQrPaymentCredentials,
		metric: "grpc-qr-payment-credentials",
		code: "GET_QR_PAYMENT_CREDENTIALS",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "qrUrl", type: "string", maxLen: 1000, required: true }
		]
	},
	MAKE_QR_PAYMENT: {
		funcName: "qrPaymentController",
		func: qrPaymentController,
		metric: "grpc-make-qr-payment",
		code: "MAKE_QR_PAYMENT",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "clientType", type: "string", maxLen: 300, required: true },
			{ name: "qrVersion", type: "string", maxLen: 300, required: true },
			{ name: "qrType", type: "string", maxLen: 300, required: true },
			{ name: "qrType", type: "string", maxLen: 300, required: true },
			{ name: "qrMerchantProviderId", type: "string", maxLen: 300, required: true },
			{ name: "qrMerchantId", type: "string", maxLen: 300, required: false },
			{ name: "qrServiceId", type: "string", maxLen: 300, required: false },
			{ name: "qrAccount", type: "string", maxLen: 300, required: false },
			{ name: "qrMcc", type: "string", maxLen: 300, required: false },
			{ name: "qrCcy", type: "string", maxLen: 300, required: false },
			{ name: "qrTransactionId", type: "string", maxLen: 300, required: false },
			{ name: "qrServiceName", type: "string", maxLen: 300, required: false },
			{ name: "qrComment", type: "string", maxLen: 300, required: false },
			{ name: "qrControlSum", type: "string", maxLen: 300, required: false },
			{ name: "amount", type: "string", maxLen: 300, required: true },
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "qrAccountChangeable", type: "boolean", required: false },
		]
	},
	DIGITAL_LOAN_MAKE_REPAYMENT: {
		funcName: "digitalLoanMakeRepaymentController",
		func: digitalLoanMakeRepaymentController,
		metric: "grpc-digital-loan-make-repayment-controller",
		code: "DIGITAL_LOAN_MAKE_REPAYMENT",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "operationId", type: "string", maxLen: 64, required: true },
			{ name: "accountIdDebit", type: "integer", maxLen: 32, required: true },
			{ name: "amountDebit", type: "string", maxLen: 20, required: true },
			{ name: "loanNumber", type: "string", maxLen: 64, required: true },
			{ name: "loanType", type: "string", maxLen: 64, required: true },
			{ name: "isDigitalLoanFullRepayment", type: "boolean", required: false },
		]
	},
	MAKE_MONEY_EXPRESS: {
		funcName: "moneyExpressOutController",
		func: moneyExpressOutController,
		metric: "money-express-out-controller",
		code: "MAKE_MONEY_EXPRESS",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "operationId", type: "string", maxLen: 64, required: true },
			{ name: "accountIdDebit", type: "integer", maxLen: 32, required: true },
			{ name: "amountCredit", type: "string", maxLen: 20, required: true },
			{ name: "creditCcy", type: "string", maxLen: 3, minLen: 3, required: false },
			{ name: "recipientName", type: "string", maxLen: 100, required: true },
			{ name: "accountCreditPropValue", type: "string", maxLen: 20, required: true },
			{ name: "accountCreditPropType", type: "string", maxLen: 20, required: true },
			{ name: "receiverCity", type: "string", maxLen: 25, required: false },
			{ name: "receiverStreetAddress", type: "string", maxLen: 99, required: false },
			{ name: "valueDate", type: "string", maxLen: 32, minLen: 1, required: false },
			{ name: "theirRefNo", type: "string", maxLen: 32, minLen: 0, required: false },
			{ name: "paymentPurpose", type: "string", maxLen: 200, minLen: 0, required: false },
		]
	},
	MAKE_VISA_2_VISA_OCT: {
		funcName: "visa2visaOctController",
		func: visa2visaOctController,
		metric: "grpc-visa-2-visa-oct-controller",
		code: "MAKE_VISA_2_VISA_OCT",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "operationId", type: "string", maxLen: 64, required: true },
			{ name: "accountIdDebit", type: "integer", maxLen: 32, required: true },
			{ name: "amountDebit", type: "string", maxLen: 20, required: true },
			{ name: "recipientName", type: "string", maxLen: 100, required: false },
			{ name: "accountCreditPropValue", type: "string", maxLen: 20, required: true },
			{ name: "accountCreditPropType", type: "string", maxLen: 20, required: true },
			{ name: "receiverCity", type: "string", maxLen: 25, required: false },
			{ name: "receiverStreetAddress", type: "string", maxLen: 99, required: false },
			{ name: "provinceCode", type: "string", maxLen: 2, required: false },
		]
	},
	MAKE_VISA_2_VISA_OCT_ADD_FIELDS: {
		funcName: "showAdditionalFieldsByPhoneOrCardPan",
		func: showAdditionalFieldsByPhoneOrCardPan,
		metric: "grpc-showAdditionalFieldsByPhoneOrCardPan",
		code: "MAKE_VISA_2_VISA_OCT",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "type", type: "string", maxLen: 20, required: false },
			{ name: "value", type: "string", maxLen: 64, required: false },
		]
	},
	MAKE_VISA_2_VISA_AFT: {
		funcName: "visa2visaAftController",
		func: visa2visaAftController,
		metric: "grpc-visa-2-visa-aft-controller",
		code: "MAKE_VISA_2_VISA_AFT",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "operationId", type: "string", maxLen: 64, required: true },
			{ name: "accountIdCredit", type: "integer", maxLen: 32, required: true },
			{ name: "amountCredit", type: "string", maxLen: 20, required: true },
			{ name: "receiverCardPan", type: "string", maxLen: 16, required: false },
			{ name: "receiverName", type: "string", maxLen: 100, required: true },
			{ name: "receiverCardExpiry", type: "string", maxLen: 10, required: true },
			{ name: "receiverCardCvv2", type: "string", maxLen: 6, required: true }
		]
	},
	MAKE_IMMOVABLE_SALYK_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		headerParams: ALLOWED_HEADER_PARAMS,
		code: "MAKE_IMMOVABLE_SALYK_PAYMENT",
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "tin", type: "string", maxLen: 14, required: false},
			{name: "eniCode", type: "string", maxLen: 20, required: false},
			{name: "year", type: "string", maxLen: 4, required: false},
			{name: "immovablePropertyType", type: "string", maxLen: 20, required: false},
			{name: "zonalRatio", type: "string", maxLen: 20, required: false},
			{name: "functionalRatio", type: "string", maxLen: 20, required: false},
			{name: "bns", type: "string", maxLen: 20, required: false},
			{name: "nonTaxableArea", type: "string", maxLen: 20, required: false},
			{name: "paymentSum", type: "string", maxLen: 20, required: false},
			{name: "paymentCode", type: "string", required: false},
			{ name: "countrySideCode", type: "string", required: false, minLen:1},
			{ name: "countrySideName", type: "string", required: false, minLen:1},
		]
	},
	MAKE_MOVABLE_SALYK_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		headerParams: ALLOWED_HEADER_PARAMS,
		code: "MAKE_MOVABLE_SALYK_PAYMENT",
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{name: "tin", type: "string", required: false, minLen:1, maxLen:14 },
			{name: "year", type: "string", required: false, minLen:1 },
			{name:"govPlate", type:"string", required:false},
			{name:"balanceCost", type:"string", required:false},
			{name: "paymentCode", type: "string", required: false},
			{ name: "countrySideCode", type: "string", required: false, minLen:1},
			{ name: "countrySideName", type: "string", required: false, minLen:1},
		]
	},
	MAKE_MOI_DOM_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		headerParams: ALLOWED_HEADER_PARAMS,
		code: "MAKE_MOIDOM_PAYMENT",
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 45, required: true},
			{name: "propValue", type: "string", maxLen: 45, required: true},
			{name: "moidomServices", type: "object", required: true},
			{name: "amountCredit", type: "string", maxLen: 32, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 32, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "theirRefNo", type: "string", maxLen: 32, minLen: 0, required: false},
			{name: "txnId", type: "integer", maxLen: 16, minLen: 1, required: false},
			{name: "paymentCode", type: "string", required: false}, // MOI_DOM
		]
	},
	MAKE_OTHER_TAX_SALYK_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		headerParams: ALLOWED_HEADER_PARAMS,
		code: "MAKE_OTHER_TAX_SALYK_PAYMENT",
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: true},
			{ name: "tin", type: "string", required: false, minLen:1, maxLen:14 },
			{ name: "rayonCode", type: "string", required: false, minLen:1},
			{ name: "rayonName", type: "string", required: false, minLen:1},
			{ name: "countrySideCode", type: "string", required: false, minLen:1},
			{ name: "countrySideName", type: "string", required: false, minLen:1},
			{ name: "taxCode", type: "string", required: false, minLen:1},
			{ name: "taxName", type: "string", required: false, minLen:1},
			{ name: "chapterCode", type: "string", required: false, minLen:1},
			{ name: "chapterName", type: "string", required: false, minLen:1},
			{name: "paymentCode", type: "string", required: false},

		]
	},
	MAKE_SAFE_CITY_FINES_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-paymentController",
		headerParams: ALLOWED_HEADER_PARAMS,
		code: "MAKE_SAFE_CITY_FINES_PAYMENT",
		bodyParams: [
			{name: "operationId", type: "string", maxLen: 64, required: true},
			{name: "serviceProviderId", type: "integer", maxLen: 15, required: true},
			{name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{name: "propValue", type: "string", maxLen: 50, required: true},
			{name: "amountCredit", type: "string", maxLen: 20, required: false},
			{name: "inn", type: "string", required: false, minLen:1, maxLen:14 },
			{name: "violationTitle", type: "string", required: false},
			{name: "violationType", type: "string", required: false},
			{name: "plateNumber", type: "string", required: false},
			{name: "protocolNumber", type: "string", required: false},
		]
	},
	MAKE_DISTRIBUTION_OPERATIONS: {
		funcName: "makeDistributionOperations",
		func: makeDistributionOperations,
		metric:  "grpc-makeDistributionOperations",
		headerParams: ALLOWED_HEADER_PARAMS,
		code: "MAKE_DISTRIBUTION_OPERATIONS",
		bodyParams: [
			{ name: "method", type: "string", required: true },
			{ name: "distributor", type: "string", required: true },
			{ name: "data", type: "object", required: true },
		],
	},
	MAKE_CAR_INSURANCE_PAYMENT: {
		funcName: "paymentController",
		func: paymentController,
		metric: "grpc-payment-handler",
		code: "MAKE_CAR_INSURANCE_PAYMENT",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "operationId", type: "string", maxLen: 45, required: true },
			{ name: "insurer", type: "string", required: true, minLen: 1, maxLen: 10 },
			{ name: "serviceProviderId", type: "integer", maxLen: 32, required: true},
			{ name: "accountIdDebit", type: "integer", maxLen: 32, required: true},
			{ name: "person", type: "object", required: true },
			{ name: "car", type: "object", required: true },
			{ name: "certificate", type: "object", required: true },
			{ name: "periodDays", type: "integer", required: true },
			{ name: "unlimitedDrivers", type: "integer", required: true },
			{ name: "carCodeCarOfUse", type: "string", required: true },
			{ name: "hasTechOsmotr", type: "boolean", required: true },
			{ name: "techOsmotrNumber", type: "string", required: false },
			{ name: "techOsmotrFromDate", type: "date", required: false },
			{ name: "techOsmotrToDate", type: "date", required: false },
			{ name: "enginePower", type: "float", required: false },
			{ name: "startDate", type: "date", required: false },
			{ name: "endDate", type: "date", required: false },
		]
	},
	MAKE_MASTERCARD_2_MASTERCARD: {
		funcName: "mastercard2mastercardController",
		func: mastercard2mastercardController,
		metric: "grpc-mastercard2mastercardController",
		code: "MAKE_MASTERCARD_2_MASTERCARD",
		headerParams: ALLOWED_HEADER_PARAMS,
		bodyParams: [
			{ name: "operationId", type: "string", maxLen: 64, required: true },
			{ name: "accountIdDebit", type: "integer", maxLen: 32, required: true },
			{ name: "amountDebit", type: "string", maxLen: 20, required: true },
			{ name: "recipientName", type: "string", maxLen: 100, required: false },
			{ name: "accountCreditPropValue", type: "string", maxLen: 20, required: true },
			{ name: "accountCreditPropType", type: "string", maxLen: 20, required: true },
		]
	},
};

exports.start = async function () {

	log.debug("Загрузка сервиса Transfer Api");

	const servicePackage = prepareServicePackage();

	grpcServer = new grpc.Server({
		"grpc.max_receive_message_length": 1024 * 1024 * 100,
		"grpc.max_send_message_length": 1024 * 1024 * 100
	});

	grpcServer.addService(servicePackage[state.SERVICES.WEB_TRANSFER_API].service, {
		makeWebTransfer: transferHandler,
	});

	grpcServer.addService(servicePackage[state.SERVICES.WEB_PAYMENT_API].service, {
		makeWebPayment: paymentsHandler
	});

	grpcServer.bindAsync(`${config.config.main.apiBindIp}:${config.config.main.apiTcpPort}`,
		grpc.ServerCredentials.createInsecure(), function (error) {
			if (error) {
				log.error("Ошибка при инициализации сервиса Web Transfer Api", null, error);
				process.exit(1);
			}
			log.debug(`Web Transfer Api привязан к порту: ${config.config.main.apiTcpPort}`);
			log.info("Web Transfer Api запущен!");
			grpcServer.start();
		});

};


async function transferHandler(call, callback) {
	log.debug(`Вызван метод transferHandler ${call.request.code}`);
	const code = call.request.code;

	if (!code) {
		log.error("Не передан код операции!");
		callback(null, responseHandler.createFailedResponse(state.ERROR_CODES.INVALID_REQUEST));
		return;
	}

	if (typeof code !== "string") {
		log.error("Неверный тип данных кода операции");
		callback(null, responseHandler.createFailedResponse(state.ERROR_CODES.INVALID_REQUEST));
		return;
	}

	const methodObject = exports.methodObjects[code];

	if (!methodObject) {
		log.error(`Перевод по коду ${code} не найден!`);
		callback(null, responseHandler.createFailedResponse(state.ERROR_CODES.INVALID_REQUEST));
		return;
	}

	await invokeApi(call, callback, methodObject, code);
}


async function paymentsHandler(call, callback) {
	log.debug("Вызван метод paymentsHandler");

	const code = call.request.code;

	if (!code) {
		log.error("Не передан код операции!");
		callback(null, responseHandler.createFailedResponse(state.ERROR_CODES.INVALID_REQUEST));
		return;
	}

	if (typeof code !== "string") {
		log.error("Неверный тип данных кода операции");
		callback(null, responseHandler.createFailedResponse(state.ERROR_CODES.INVALID_REQUEST));
		return;
	}

	const methodObject = exports.methodObjects[code];

	if (!methodObject) {
		log.error(`Платеж по коду ${code} не найден!`);
		callback(null, responseHandler.createFailedResponse(state.ERROR_CODES.INVALID_REQUEST));
		return;
	}

	await invokeApi(call, callback, methodObject, code);
}

async function invokeApi(call, callback, methodObject, code) {

	let refId = call.metadata.get("refId")[0];
	log.debug("Запущен метод invokeApi.", refId);
	let bodyParams = JSON.parse(call.request.data);
	let extractedHeaders = {};

	for (let headerParam of methodObject.headerParams) {
		const key = headerParam["name"];
		const value = call.metadata.get(key)[0];
		extractedHeaders[key] = value;
	}
	let headersValidated = {};
	let bodyParamsValidated = {};

	try {
		headersValidated = verifyParamsList(extractedHeaders, methodObject, "headerParams", refId);
		bodyParamsValidated = verifyParamsList(bodyParams, methodObject, "bodyParams", refId);
	} catch (error) {
		log.error("Возникла ошибка в методе invokeApi", error, refId);
		retApiError(error, methodObject, call, callback, refId);
		return;
	}

	headersValidated.paymentCode = code;
	const apiFunc = methodObject["func"];

	apiFunc(call, headersValidated, bodyParamsValidated, refId, function (error, response) {
		if (error) {
			retApiError(error, methodObject, call, callback, refId, response);
			return;
		}
		log.trace("Завершен запуск метода API " + methodObject["funcName"], refId);

		callback(null, responseHandler.createSuccessfulResponse(response));
		return;
	});
}

function retApiError(apiErr, methodObject, call, callback, refId, response = null) {

	const logRec = {
		code: apiErr,
		error: "Ошибка выполнения API запроса " + methodObject["funcName"],
		sysErr: null,
		refId: refId,
	};

	log.rec(logRec);
	callback(null, responseHandler.createFailedResponse(apiErr, response));

	log.rec({
		info: "Вернули ответ с ошибкой.",
		trace: `Параметры: код ошибки: ${apiErr}.`,
		refId
	});

	return;
}

function verifyParamsList(paramsObj, methodObj, paramListName, refId) {
	log.debug("Запущен метод verifyParamsList", refId);

	let retObj = {};

	if (methodObj[paramListName]) {
		for (let i = 0; i < methodObj[paramListName].length; i++) {
			let confParam = methodObj[paramListName][i];
			let param = null;
			let paramFin = null;

			for (let ind in paramsObj) {
				if (ind === confParam["name"]) {
					param = paramsObj[ind];
					break;
				}
			}

			try {
				paramFin = verifyParam(param, confParam, methodObj, refId);
			} catch (err) {
				log.error("Параметр не прошел проверку формата. Метод: " + methodObj["funcName"] + ". Параметр: " + confParam["name"] + ". Значение параметра: " +
					xssFilters.inHTMLData(param) + ". Требуемый формат: " + JSON.stringify(confParam) + ". Ошибка: ", err, refId);
				//retApiError('E_IncorrectParams', req, res, refId);
				throw "E_IncorrectParams";
			}

			retObj[confParam["name"]] = paramFin;
		}
	}

	return retObj;
}

function verifyParam(paramVal, confParam, methodObj, refId) {
	log.debug("Вызван метод verifyParam", refId);
	log.trace(`Параметры для verifyParam: ${JSON.stringify(paramVal)}, ${JSON.stringify(confParam)}}`, refId);
	let retParam = null;
	let paramChecked = false;

	// Проверка на обязательность параметра

	if (paramVal == null && confParam["required"] == true) {
		log.error("Вызов метода без указания обязательного параметра. Метод: " + methodObj["funcName"] + ". Отсутствующий параметр: " + confParam["name"] + ". Ref: " + refId);
		throw "E_IncorrectParams";
	}

	// if (paramVal.length === 0) {
	//     log.error("Вызов метода с пустым параметром: " + confParam["name"], null, refId);
	//     throw "E_IncorrectParams";
	//
	// }
	// Проверка параметра

	if (paramVal != null) {
		let cType = confParam["type"];

		if (!["integer", "string", "string-asci", "string-num", "float", "money", "date", "object", "array", "boolean", "phone", "email"].includes(cType)) {
			log.error("В конфигурации определен параметр неизвестного типа: " + cType + ". Ref: " + refId);
			throw "E_IncorrectParams";
		}

		let cLen = confParam["maxLen"];
		let cMinLen = confParam["minLen"];

		// Конвертируем параметр в строку
		let paramValStr = paramVal.toString();
		if (Array.isArray(paramVal) || typeof paramVal === "object") {
			paramValStr = JSON.stringify(paramVal);
		}

		// Проверяем длину объекта в строковом выражении
		if(cMinLen && paramValStr.length < cMinLen){
			log.error("Вызов метода с параметром,  не достигающим допустимой минимальной длины. Метод: " + methodObj["funcName"] +
			". Параметр: " + confParam["name"] + ". Фактическая длина: " + paramValStr.length + ". Допустимая длина: " + cMinLen +  ". Ref: " + refId);
			throw "E_IncorrectParams";
		}

		if (paramValStr.length > cLen) {
			log.error("Вызов метода с параметром, превышающим допустимую длину. Метод: " + methodObj["funcName"] +
				". Параметр: " + confParam["name"] + ". Фактическая длина: " + paramValStr.length + ". Допустимая длина: " + cLen + ". Ref: " + refId);
			throw "E_IncorrectParams";
		}
		// Проверяем параметр на XSS (внедрение JavaScript кода)
		if (paramValStr !== xssFilters.inHTMLData(paramValStr)) {
			log.error("Обнаружена попытка внедрения XSS. Метод: " + methodObj["funcName"] + ". Параметр: " + confParam["name"] + ". Результат XSS обработчика: " + xssFilters.inHTMLData(paramValStr) + ". Ref: " + refId);
			throw "E_IncorrectParams";
		}

		// Проверяем тип параметра (и приводим к нужному типу или формату при необходимости)
		if (cType == "integer") {
			// Проверка
			if (!validator.isInt(paramValStr)) throw "E_IncorrectParams";
			// Приведение
			retParam = parseInt(paramValStr);
			paramChecked = true;
		}

		if (cType == "string") {
			// Проверка (может быть любая строка)
			// Приведение
			retParam = xssFilters.inHTMLData(paramValStr);
			paramChecked = true;
		}

		if (cType == "string-asci") {
			// Проверка (Строка с символами из ACSI)
			if (!validator.isAscii(paramValStr)) throw "E_IncorrectParams";
			// Приведение
			retParam = xssFilters.inHTMLData(paramValStr);
			paramChecked = true;
		}

		if (cType == "string-num") {
			// Проверка (Строка с числами)
			if (!validator.isInt(paramValStr, {allow_leading_zeroes: true})) throw "E_IncorrectParams";
			// Приведение
			retParam = xssFilters.inHTMLData(paramValStr);
			paramChecked = true;
		}

		if (cType == "float") {
			// Проверка (число с плавающей точкой)
			if (!validator.isFloat(paramValStr)) throw "E_IncorrectParams";
			// Приведение (не округляем, берем как есть)
			retParam = parseFloat(paramValStr);
			paramChecked = true;
		}

		if (cType == "money") {
			// Проверка (число с плавающей точкой)
			if (!validator.isFloat(paramValStr)) throw "E_IncorrectParams";
			// Приведение (округляем до двух знаков после запятой)
			retParam = parseFloat(paramValStr);
			retParam = Math.round(retParam * 100) / 100;
			paramChecked = true;
		}

		if (cType == "date") {
			// Проверка (ISO дата)
			if (!validator.isISO8601(paramValStr, {strict: true})) throw "E_IncorrectParams";
			// Приведение (Конвертим в moment() и обратно)
			//retParam = moment(paramValStr).format('YYYY-MM-DD');
			retParam = paramValStr;
			paramChecked = true;
		}

		if (cType == "object") {
			// Проверка (на JSON)
			if (!validator.isJSON(paramValStr)) throw "E_IncorrectParams";
			// Приведение (конвертим в объект и проверяем, объект ли это)
			retParam = JSON.parse(xssFilters.inHTMLData(paramValStr));
			if (Array.isArray(retParam)) throw "E_IncorrectParams";
			paramChecked = true;
		}

		if (cType == "array") {
			// Проверка (на JSON)
			if (!validator.isJSON(paramValStr)) throw "E_IncorrectParams";
			// Приведение (конвертим в объект и проверяем, объект ли это)
			retParam = JSON.parse(xssFilters.inHTMLData(paramValStr));
			if (!Array.isArray(retParam)) throw "E_IncorrectParams";
			paramChecked = true;
		}

		if (cType == "boolean") {
			// Проверка
			if (!["1", "true", "0", "false"].includes(paramValStr)) throw "E_IncorrectParams";
			// Приведение
			retParam = validator.toBoolean(paramValStr, true);
			paramChecked = true;
		}

		if (cType == "phone") {
			// Проверка (также как string-num, только убираем + в начале, если он есть)
			if (paramValStr.startsWith("+")) paramValStr = paramValStr.substring(1);
			if (!validator.isInt(paramValStr, {allow_leading_zeroes: true})) throw "E_IncorrectParams";

			// Приведение
			retParam = paramValStr;
			paramChecked = true;
		}

		if (cType == "email") {

			// Проверка
			if (!validator.isEmail(paramValStr)) throw "E_IncorrectParams";
			// Приведение
			retParam = xssFilters.inHTMLData(paramValStr);
			paramChecked = true;
		}

		if (!paramChecked) {
			log.error("Параметр не проверен ни одной из функций валидации. Метод: " + methodObj["funcName"] + ". Параметр: " + JSON.stringify(confParam) + ". Ref: " + refId);
			throw "E_IncorrectParams";
		}
	}
	return retParam;
}


exports.stop = function () {
	grpcServer.forceShutdown();
	log.info("Transfer Api остановлен!");
};

function prepareServicePackage() {
	log.trace("Вызван prepareServicePackage");
	var protoFile = getProtoFile(transfer_api_protofile_name);

	packageDefinition = protoLoader.loadSync(protoFile,
		{
			keepCase: true,
			longs: String,
			enums: String,
			defaults: true,
			oneofs: true
		}
	);

	grpcServicePackage = grpc.loadPackageDefinition(packageDefinition)[state.transferApiProtofilePackageName]; //package name

	return grpcServicePackage;
}
