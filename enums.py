import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    BUYER = "buyer"
    SELLER = "seller"
    CANDIDATE = "candidate"
    DEVELOPER = "developer"
    RECRUITER = "recruiter"
    MODERATOR = "moderator"

class OrderStatus(enum.Enum):
    PLACED = "Order Placed"
    CONFIRMED = "Confirmed"
    SHIPPED = "Shipped"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"
    RETURNED = "Returned"

class InvoiceStatus(enum.Enum):
    UNPAID = "Unpaid"
    PAID = "Paid"
    OVERDUE = "Overdue"
    CANCELLED = "Cancelled"

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