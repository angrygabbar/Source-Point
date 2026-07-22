import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    BUYER = "buyer"
    SELLER = "seller"
    CANDIDATE = "candidate"
    DEVELOPER = "developer"
    RECRUITER = "recruiter"
    MODERATOR = "moderator"

class RollbackRequestStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class RollbackTermsDecision(enum.Enum):
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"

class OrderStatus(enum.Enum):

    PLACED = "Order Placed"
    ACCEPTED = "Order Accepted"
    CONFIRMED = "Order Accepted"
    PAYMENT_RECEIVED = "Payment Received"
    PACKED = "Packed"
    DISPATCHED = "Order Dispatched"
    SHIPPED = "Shipped"
    IN_TRANSIT = "In Transit"
    OUT_FOR_DELIVERY = "Out for Delivery"
    DELIVERED = "Order Delivered"
    CANCELLED = "Order Cancelled"
    RETURNED = "Returned"

class InvoiceStatus(enum.Enum):
    UNPAID = "Unpaid"
    PAID = "Paid"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"

class SupersCoinTransactionType(enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"

class SupersCoinInvoiceStatus(enum.Enum):
    UNPAID = "Unpaid"
    PAID = "Paid"
    CANCELLED = "Cancelled"

class CoinSpendingCategory(enum.Enum):
    HOTEL_BOOKING = "Hotel Booking"
    BUS_BOOKING = "Bus Booking"
    FLIGHT_BOOKING = "Flight Booking"
    OTHER = "Other"

class JobStatus(enum.Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    DRAFT = "Draft"

class ApplicationStatus(enum.Enum):
    PENDING = "Pending"
    REVIEWING = "Under Review"
    ACCEPTED = "Selected"
    REJECTED = "Rejected"

class PaymentStatus(enum.Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"

class GiftCardStatus(enum.Enum):
    AVAILABLE = "Available"
    SENT = "Sent"
    EXPIRED = "Expired"

class VoucherOrderStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class GiftCardBrand(enum.Enum):
    # ── Food & Delivery ──
    ZOMATO = "Zomato"
    SWIGGY = "Swiggy"
    DOMINOS = "Domino's"
    MCDONALDS = "McDonald's"
    KFC = "KFC"
    PIZZA_HUT = "Pizza Hut"
    STARBUCKS = "Starbucks"
    BARBEQUE_NATION = "Barbeque Nation"
    HALDIRAMS = "Haldiram's"
    BASKIN_ROBBINS = "Baskin Robbins"
    BURGER_KING = "Burger King"
    SUBWAY = "Subway"
    CHAAYOS = "Chaayos"
    # ── E-Commerce ──
    AMAZON = "Amazon"
    FLIPKART = "Flipkart"
    MYNTRA = "Myntra"
    AJIO = "Ajio"
    NYKAA = "Nykaa"
    MEESHO = "Meesho"
    TATA_CLIQ = "Tata CLiQ"
    FIRSTCRY = "FirstCry"
    # ── Entertainment ──
    PVR_INOX = "PVR INOX"
    BOOKMYSHOW = "BookMyShow"
    NETFLIX = "Netflix"
    HOTSTAR = "Disney+ Hotstar"
    SPOTIFY = "Spotify"
    YOUTUBE_PREMIUM = "YouTube Premium"
    GAANA = "Gaana"
    JIOCINEMA = "JioCinema"
    SONYLIV = "Sony LIV"
    ZEE5 = "Zee5"
    APPLE_ITUNES = "Apple / iTunes"
    # ── Travel & Stay ──
    MAKEMYTRIP = "MakeMyTrip"
    YATRA = "Yatra"
    CLEARTRIP = "Cleartrip"
    IRCTC = "IRCTC"
    OYO = "OYO Rooms"
    EASEMYTRIP = "EaseMyTrip"
    GOIBIBO = "Goibibo"
    # ── Payments & Wallets ──
    PAYTM = "Paytm"
    PHONEPE = "PhonePe"
    GOOGLE_PAY = "Google Pay"
    # ── Fashion & Lifestyle ──
    LIFESTYLE = "Lifestyle"
    SHOPPERS_STOP = "Shoppers Stop"
    PANTALOONS = "Pantaloons"
    WESTSIDE = "Westside"
    CROMA = "Croma"
    RELIANCE_DIGITAL = "Reliance Digital"
    TITAN = "Titan"
    TANISHQ = "Tanishq"
    LENSKART = "Lenskart"
    BATA = "Bata"
    # ── Fuel & Transport ──
    HPCL = "HPCL"
    IOCL = "IOCL"
    BPCL = "BPCL"
    UBER = "Uber"
    OLA = "Ola"
    # ── Grocery & Supermarket ──
    BIGBASKET = "BigBasket"
    JIOMART = "JioMart"
    DMART = "DMart"
    SPENCERS = "Spencer's"
    MORE = "More Supermarket"
    ZEPTO = "Zepto"
    BLINKIT = "Blinkit"
    # ── Gaming ──
    GOOGLE_PLAY = "Google Play"
    STEAM = "Steam"
    PLAYSTATION = "PlayStation"
    XBOX = "Xbox"
    # ── Other ──
    OTHER = "Other"

class AssetType(enum.Enum):
    LAPTOP = "Laptop"
    SERVER = "Server"
    MONITOR = "Monitor"
    KEYBOARD = "Keyboard"
    MOUSE = "Mouse"
    HEADPHONE = "Headphone"
    MOBILE = "Mobile"
    TABLET = "Tablet"
    PRINTER = "Printer"
    NETWORKING = "Networking"
    STORAGE = "Storage"
    CHARGER = "Charger"
    CABLE = "Cable"
    OTHER = "Other"

class AssetStatus(enum.Enum):
    ACTIVE = "Active"
    IN_STORAGE = "In Storage"
    UNDER_REPAIR = "Under Repair"
    RETIRED = "Retired"
    LOST = "Lost"

class AssetCondition(enum.Enum):
    NEW = "New"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
