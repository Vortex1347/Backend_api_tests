# ===== НАСТРОЙКИ ПОДКЛЮЧЕНИЯ =====
GRPC_SERVER_URL = 'newibanktest.kicb.net:443'
GRPC_OPTIONS = [
    ('grpc.enable_http_proxy', 0),
    ('grpc.keepalive_timeout_ms', 10000)
]

# ===== НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ДЛЯ IPC СЕРВИСА =====
IPC_GRPC_SERVER_URL = 'localhost:1111'  
IPC_GRPC_OPTIONS = [
    ('grpc.enable_http_proxy', 0),
    ('grpc.keepalive_timeout_ms', 10000),
    ('grpc.keepalive_time_ms', 30000),
    ('grpc.keepalive_permit_without_calls', True),
    ('grpc.http2.max_pings_without_data', 0),
    ('grpc.http2.min_time_between_pings_ms', 10000),
    ('grpc.http2.min_ping_interval_without_data_ms', 300000),
    ('grpc.max_connection_idle_ms', 30000),
    ('grpc.max_connection_age_ms', 300000),
]

# ===== НАСТРОЙКИ ПОДКЛЮЧЕНИЯ ДЛЯ ADMIN API =====
ADMIN_API_URL = 'http://192.168.190.46:55556'

# ===== КОДЫ ЗАПРОСОВ =====
CODE_CREATE_TRANSFER = "MAKE_BANK_CLIENT_TRANSFER"
CODE_CONFIRM_TRANSFER = "CONFIRM_TRANSFER"
CODE_MAKE_TXN_SHOP_OPERATION = "MAKE_TXN_SHOP_OPERATION"
CODE_MAKE_MONEY_TRANSFER = "MAKE_MONEY_TRANSFER"
CODE_MAKE_SHOP_OPERATION = "MAKE_SHOP_OPERATION"
CODE_MAKE_MONEY_EXPRESS = "MAKE_MONEY_EXPRESS"
CODE_MAKE_OTHER_BANK_TRANSFER = "MAKE_OTHER_BANK_TRANSFER"
CODE_MAKE_OWN_ACCOUNTS_TRANSFER = "MAKE_OWN_ACCOUNTS_TRANSFER"
CODE_MAKE_GENERIC_PAYMENT_V2 = "MAKE_GENERIC_PAYMENT_V2"
CODE_MAKE_MOI_DOM_PAYMENT = "MAKE_MOI_DOM_PAYMENT"
CODE_MAKE_QR_PAYMENT = "MAKE_QR_PAYMENT"
CODE_MAKE_SWIFT_TRANSFER = "MAKE_SWIFT_TRANSFER"
CODE_MAKE_DEPOSIT = "MAKE_DEPOSIT"
CODE_DIGITAL_LOAN_APPLY = "DIGITAL_LOAN_APPLY"
CODE_DIGITAL_LOAN_CHECK_SERVICE = "DIGITAL_LOAN_CHECK_SERVICE"

# ===== НАСТРОЙКИ УСТРОЙСТВА =====
DEVICE_TYPE = 'ios'
USER_AGENT = '12; iPhone12MaxProDan'

# ===== ДАННЫЕ СЕССИИ =====
SESSION_KEY = '7C17ZJOKrOlYPvkoeQ835L'  # TODO: Заполнить session key для gRPC переводов
ADMIN_SESSION_KEY = '762LmmDOQXTuLnDRr3mmIr'  # Session key для Admin API

# ===== OTP КОД =====
OTP_CODE = "111111"  # TODO: Заполнить OTP код

# ===== ОБЩИЕ ДАННЫЕ =====
# Счета
ACCOUNT_ID_DEBIT = 17420  # TODO: Заполнить основной ID счета списания

# Суммы
AMOUNT_100 = "100"  # Стандартная сумма 100
AMOUNT_SMALL = "1"  # Малая сумма для тестов

# Контактные данные
PHONE_NUMBER = "+996555599256"  # TODO: Заполнить номер телефона
EMAIL = "blvckvortex@mail.ru"  # TODO: Заполнить email

# Доставка
DELIVERY_TYPE = "bank"  # Тип доставки
BRANCH_CODE = "511"  # TODO: Заполнить код филиала

# Языки и валюты
STATEMENT_LANGUAGE = "ru"  # Язык выписок/справок
CURRENCY_KGS = "KGS"
CURRENCY_USD = "USD"
CURRENCY_RUB = "RUB"
CURRENCY_TRY = "TRY"

# ===== ДАННЫЕ ДЛЯ БАНКОВСКОГО ПЕРЕВОДА =====
ACCOUNT_CREDIT = "1280016029401016"  # TODO: Заполнить номер счета зачисления
ACCOUNT_CREDIT_PROP_TYPE = "ACCOUNT_NO"
TRANSFER_AMOUNT = "137.00"  # TODO: Заполнить сумму перевода
PAYMENT_PURPOSE = "Пополнение счета"

# ===== ДАННЫЕ ДЛЯ ОТКРЫТИЯ СЧЕТА =====
OPEN_ACCOUNT_CCY = CURRENCY_TRY  # TODO: Заполнить валюту открываемого счета
PRODUCT_TYPE_ACCOUNT_OPENING = "makeAccountOpeningApplication"

# ===== ДАННЫЕ ДЛЯ ЗАПРОСА ВЫПИСКИ =====
ACCOUNT_DEBIT_IDS = [ACCOUNT_ID_DEBIT]  # Список ID счетов для выписки
PRODUCT_TYPE_STATEMENT = "makeAccountStatementRequest"

# ===== ДАННЫЕ ДЛЯ ПЛАТЕЖА ASTROSEND =====
ASTROSEND_AMOUNT_CREDIT = "500"
MONEY_TRANSFER_TYPE = "ASTRASEND_OUT"
CREDIT_CCY = CURRENCY_RUB
RECIPIENT_COUNTRY_CODE = "KAZ"
RECIPIENT_FIRST_NAME = "Bularov"
RECIPIENT_LAST_NAME = "Temirlan"
MARKETING_FLAG = "true"
PROP_VALUE = "Акай"

# ===== ДАННЫЕ ДЛЯ ЗАПРОСА ЧЕКОВОЙ КНИЖКИ =====
AMOUNT_OF_CHECKBOOKS = "1"
TRUSTED_EMPLOYEE_FULL_NAME = "test"
PASSPORT_ID = "an34343434"
ISSUED_BY = "mkk40"
DATE_OF_ISSUE = "11.02.2025"
CHECKBOOK_FEE = "152.68"
PRODUCT_TYPE_CHECKBOOK = "makeCheckbookRequest"

# ===== ДАННЫЕ ДЛЯ КЛИРИНГ/ГРОСС ПЕРЕВОДА =====
TRANSFER_CLEARING_GROSS = "C"  # C - клиринг, G - гросс
VALUE_DATE = "2025-07-30"
RECIPIENT_NAME = "ОсОО Скай Мобайл "
RECIPIENT_BANK_BIC = "109022"
ACCOUNT_CREDIT_NUMBER = "1092220118930181"
TRANSFER_PURPOSE_TEXT = "услуги мобильной связи"
KNP = "42122700"
AMOUNT_CREDIT_CLEARING = "280.00"

# ===== ДАННЫЕ ДЛЯ ЗАПРОСА ДЕБЕТОВОЙ КАРТЫ =====
ACCOUNT_CLASS_GROUP_ID = 17
CARD_CCY = CURRENCY_USD
CODEWORD = "test"
CARD_HOLDER_NAME = "yrysbekov atai"
PRODUCT_TYPE_DEBIT_CARD = "makeDebitCardApplication"

# ===== ДАННЫЕ ДЛЯ ОБМЕНА ВАЛЮТ =====
EXCHANGE_ACCOUNT_ID_DEBIT = 17439
EXCHANGE_ACCOUNT_ID_CREDIT = ACCOUNT_ID_DEBIT
EXCHANGE_AMOUNT_DEBIT = AMOUNT_SMALL

# ===== ДАННЫЕ ДЛЯ ПЛАТЕЖЕЙ СЕРВИС-ПРОВАЙДЕРАМ =====
# KIB
KIB_PROP_VALUE = "0555599256"
KIB_SERVICE_ID = "CIB"
KIB_SERVICE_PROVIDER_ID = 936

# UMAI (BTS)
UMAI_PROP_VALUE = "0112151-0"
UMAI_SERVICE_ID = "BTS"
UMAI_SERVICE_PROVIDER_ID = 236

# Jubilee
JUBILEE_PROP_VALUE = "10-022-20-555555"
JUBILEE_SERVICE_ID = "JUBILEE"
JUBILEE_SERVICE_PROVIDER_ID = 237

# O! Деньги
O_DENGI_PROP_VALUE = "996700000294"
O_DENGI_SERVICE_ID = "O_DENGI"
O_DENGI_SERVICE_PROVIDER_ID = 925

# Айыл Банк
AIYL_BANK_PROP_VALUE = "996500776606"
AIYL_BANK_SERVICE_ID = "AIYL_BANK_PHONE_NUMBER"
AIYL_BANK_SERVICE_PROVIDER_ID = 851

# ===== ДАННЫЕ ДЛЯ ЗАПРОСА СПРАВКИ О ВЫПЛАТАХ ПО КРЕДИТУ =====
LOAN_STATEMENT_TYPE = {
    "kg": "Ипотекалык кредитти төлөө боюнча маалымкат",
    "ru": "Справка о выплатах по ипотечному кредиту",
    "eng": "Certificate of mortgage loan repayment",
    "default": "Справка о выплатах по ипотечному кредиту",
    "operationCategoryName": None
}
PRODUCT_TYPE_LOAN_STATEMENT = "makeLoanStatementRequest"

# ===== ДАННЫЕ ДЛЯ ПЛАТЕЖА МОЙ ДОМ (КОММУНАЛЬНЫЕ УСЛУГИ) =====
MOI_DOM_PROP_VALUE = "1337000311090988"
MOI_DOM_ADDRESS = "ул. Малдыбаева д. 7 кв. 30"
MOI_DOM_FULLNAME = "Умар"
MOI_DOM_SERVICES = [
    {"comservice": "vodokanal", "total": "594.30", "comserviceName": "БишкекВодоКанал"},
    {"comservice": "gazprom", "total": "616.98", "comserviceName": "Газпром Кыргызстан"},
    {"comservice": "teploenergo", "total": "0.00", "comserviceName": "Бишкектеплоэнерго"},
    {"comservice": "tazalyk", "total": "387.32", "comserviceName": "МП Тазалык"},
    {"comservice": "sever_electro", "total": "0.00", "comserviceName": "БиПЭС"}
]
MOI_DOM_AMOUNT_CREDIT = "1598.6"
MOI_DOM_SERVICE_PROVIDER_ID = 740
MOI_DOM_PAYMENT_CODE = "MOI_DOM"

# ===== ДАННЫЕ ДЛЯ QR ПЛАТЕЖА =====
QR_ACCOUNT_CREDIT_PROP_VALUE = "1285090000630562"
QR_PAYMENT_PURPOSE = PAYMENT_PURPOSE
QR_AMOUNT = AMOUNT_100
QR_PAYMENT = True
QR_ACCOUNT_CHANGEABLE = False
QR_SERVICE_NAME = "Zabrmgazpdfjfrhabrmjzfkmfnpdnf"
QR_SERVICE_ID = "01"
QR_CLIENT_TYPE = "1"
QR_VERSION = "01"
QR_TYPE = "STATIC"
QR_MERCHANT_PROVIDER_ID = "p2p.kicb.net"
QR_ACCOUNT = "1285090000630562"
QR_MCC = "9999"
QR_CCY = "417"  # KGS
QR_TRANSACTION_ID = "Zabrmgazpdfjfrhabrmjzfkmfnpdnf"
QR_CONTROL_SUM = "f72e"

# ===== ДАННЫЕ ДЛЯ SWIFT ПЕРЕВОДА =====
SWIFT_ACCOUNT_ID_DEBIT = 17434
SWIFT_AMOUNT_DEBIT = "1.00"
SWIFT_VALUE_DATE = "2025-07-30"
SWIFT_TRANSFER_CCY = CURRENCY_USD
SWIFT_RECIPIENT_ADDRESS = "test"
SWIFT_RECIPIENT_NAME = "test"
SWIFT_RECIPIENT_BANK_SWIFT = "KICBKG22"
SWIFT_RECIPIENT_ACC_NO = "KICBKG22"
SWIFT_TRANSFER_PURPOSE_TEXT = "test"
SWIFT_COMMISSION_TYPE = "OUR"
SWIFT_COMMISSION_ACCOUNT_ID = str(ACCOUNT_ID_DEBIT)

# ===== ДАННЫЕ ДЛЯ СОЗДАНИЯ ДЕПОЗИТА =====
DEPOSIT_TYPE = "Savings deposit"  # TODO: Заполнить тип депозита
DEPOSIT_ID = 1531  # TODO: Заполнить ID депозита
DEPOSIT_MAIN_INT_TYPE = "B"  # Тип начисления процентов
DEPOSIT_AMOUNT = "5000"  # TODO: Заполнить сумму депозита
DEPOSIT_CCY = CURRENCY_KGS  # Валюта депозита
DEPOSIT_RATE = "4.5"  # TODO: Заполнить процентную ставку
DEPOSIT_TERM = "3"  # TODO: Заполнить срок депозита (месяцы)
PRODUCT_TYPE_DEPOSIT = "makeDepositApplication"  # Тип продукта для депозита
# ===== ДАННЫЕ ДЛЯ MONEY EXPRESS =====
MONEY_EXPRESS_ACCOUNT_ID_DEBIT = EXCHANGE_ACCOUNT_ID_DEBIT  # ID дебетового счёта
MONEY_EXPRESS_RECIPIENT_NAME = "Lily Zhang"  # Имя получателя
MONEY_EXPRESS_ACCOUNT_CREDIT_PROP_VALUE = "8171999927660000"  # Номер карты получателя
MONEY_EXPRESS_ACCOUNT_CREDIT_PROP_TYPE = "CARD_NO"  # Тип реквизита
MONEY_EXPRESS_AMOUNT_DEBIT = "100"  # Сумма списания
MONEY_EXPRESS_PAYMENT_PURPOSE = "135"  # Код назначения платежа
