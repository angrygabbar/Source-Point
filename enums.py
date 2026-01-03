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